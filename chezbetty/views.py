from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.view import view_config, forbidden_view_config

from sqlalchemy.sql import func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import NoResultFound

from .models import *
from .models.model import *
from .models import user as __user
from .models.user import User
from .models.item import Item
from .models.transaction import Transaction, BTCDeposit, PurchaseLineItem
from .models.account import Account, VirtualAccount, CashAccount
from .models.event import Event

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException

class DepositException(Exception):
    pass

###
### HTML Pages
###

### No login needed

@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    return {}


@view_config(route_name='about', renderer='templates/about.jinja2')
def about(request):
    return {}


@view_config(route_name='items', renderer='templates/items.jinja2')
def items(request):
    items = DBSession.query(Item).filter(Item.enabled==True).order_by(Item.name).all()
    return {'items': items}


@view_config(route_name='shame', renderer='templates/shame.jinja2')
def users(request):
    users = DBSession.query(User).filter(User.balance < -5).order_by(User.balance).all()
    return {'users': users}


### Post mcard swipe

@view_config(route_name='purchase', renderer='templates/purchase.jinja2', permission='service')
def purchase(request):
    try:
        if len(request.matchdict['umid']) != 8:
            raise __user.InvalidUserException()

        user = User.from_umid(request.matchdict['umid'])
        if not user.enabled:
            request.session.flash('User is not enabled. Please contact chezbetty@umich.edu.', 'error')
            return HTTPFound(location=request.route_url('index'))

        # For Demo mode:
        items = DBSession.query(Item).filter(Item.enabled == True).order_by(Item.name).limit(6).all()

        # Pre-populate cart if returning from undone transaction
        cart = {}
        if len(request.GET) != 0:
            for (item_id, qty) in request.GET.items():
                cart[Item.from_id(int(item_id)).barcode] = int(qty)

        return {'user': user, 'items': items, 'cart': cart}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid M-Card swipe. Please try again.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='user', renderer='templates/user.jinja2', permission='service')
def user(request):
    try:
        user = User.from_umid(request.matchdict['umid'])
        if not user.enabled:
            request.session.flash('User not permitted to purchase items.', 'error')
            return HTTPFound(location=request.route_url('index'))

        # Iterate through all of the events that the user was the to_account
        # or fr_account on in the transactions
        transactions = []
        for event in user.events:
            for transaction in event.transactions:
                transactions.append(transaction)

        return {'user': user,
                'transactions': transactions}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='deposit', renderer='templates/deposit.jinja2', permission='service')
def deposit(request):
    try:
        user = User.from_umid(request.matchdict['umid'])

        try:
            btc_addr = Bitcoin.get_new_address(user.umid)
            btc_html = render('templates/btc.jinja2', {'addr': btc_addr})
        except BTCException as e:
            btc_html = ""

        return {'user': user, 'btc' : btc_html}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='event', permission='service')
def event(request):

    try:
        event = Event.from_id(request.matchdict['event_id'])
        transaction = event.transactions[0]

        # Choose which page to show based on the type of event
        if event.type == 'deposit':
            # View the deposit success page

            user = DBSession.query(User) \
                .filter(User.id==transaction.to_account_virt_id).one()

            prev_balance = user.balance - transaction.amount

            request.session.flash('Success! The deposit was added successfully', 'success')
            return render_to_response('templates/deposit_complete.jinja2',
                {'deposit': transaction,
                 'user': user,
                 'event': event,
                 'prev_balance': prev_balance}, request)

        elif event.type == 'purchase':
            # View the purchase success page
            user = DBSession.query(User) \
                .filter(User.id==transaction.fr_account_virt_id).one()

            order = {'total': transaction.amount,
                     'items': []}
            for subtrans in transaction.subtransactions:
                item = {}
                item['name'] = subtrans.item.name
                item['quantity'] = subtrans.quantity
                item['price'] = subtrans.item.price
                item['total_price'] = subtrans.amount
                order['items'].append(item)

            request.session.flash('Success! The purchase was added successfully', 'success')
            return render_to_response('templates/purchase_complete.jinja2',
                {'user': user,
                 'event': event,
                 'order': order}, request)

    except NoResultFound as e:
        # TODO: add generic failure page
        pass

@view_config(route_name='event_undo', permission='service')
def event_undo(request):
    # Lookup the transaction that the user wants to undo
    try:
        event = Event.from_id(request.matchdict['event_id'])
    except:
        request.session.flash('Error: Could not find transaction to undo.', 'error')
        return HTTPFound(location=request.route_url('index'))

    for transaction in event.transactions:

        # Make sure transaction is a deposit, the only one the user is allowed
        # to undo
        if transaction.type not in ('deposit', 'purchase'):
            request.session.flash('Error: Only deposits and purchases may be undone.', 'error')
            return HTTPFound(location=request.route_url('index'))

        # Make sure that the user who is requesting the deposit was the one who
        # actually placed the deposit.
        try:
            if transaction.type == 'deposit':
                user = User.from_id(transaction.to_account_virt_id)
            elif transaction.type == 'purchase':
                user = User.from_id(transaction.fr_account_virt_id)
        except:
            request.session.flash('Error: Invalid user for transaction.', 'error')
            return HTTPFound(location=request.route_url('index'))

        if user.umid != request.matchdict['umid']:
            request.session.flash('Error: Transaction does not belong to specified user', 'error')
            return HTTPFound(location=request.route_url('user', umid=request.matchdict['umid']))

    # If the checks pass, actually revert the transaction
    try:
        line_items = datalayer.undo_event(event)
        request.session.flash('Transaction successfully reverted.', 'success')
    except:
        request.session.flash('Error: Failed to undo transaction.', 'error')
    if event.type == 'deposit':
        return HTTPFound(location=request.route_url('user', umid=user.umid))
    elif event.type == 'purchase':
        return HTTPFound(location=request.route_url('purchase', umid=user.umid, _query=line_items))
    else:
        assert(False and "Should not be able to get here?")

###
### JSON Requests
###

@view_config(route_name='item', renderer='json', permission='user')
def item(request):
    try:
        item = Item.from_barcode(request.matchdict['barcode'])
    except:
        return {'status': 'unknown_barcode'}
    if item.enabled:
        status = 'success'
    else:
        status = 'disabled'
    item_html = render('templates/item_row.jinja2', {'item': item})
    return {'status': status, 'id':item.id, 'item_row_html' : item_html}

###
### POST Handlers
###

@view_config(route_name='purchase_new', request_method='POST', renderer='json', permission='service')
def purchase_new(request):
    try:
        user = User.from_umid(request.POST['umid'])

        # Bundle all purchase items
        items = {}
        for item_id,quantity in request.POST.items():
            if item_id == 'umid':
                continue
            item = Item.from_id(int(item_id))
            items[item] = int(quantity)

        # Commit the purchase
        purchase = datalayer.purchase(user, items)

        # Return the committed transaction ID
        return {'event_id': purchase.event.id}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid user error. Please try again.', 'error')
        return {'redirect_url': '/'}

    except ValueError as e:
        return {'error': 'Unable to parse Item ID or quantity'}

    except NoResultFound as e:
        # Could not find an item
        return {'error': 'Unable to identify an item.'}


# Handle the POST from coinbase saying Chez Betty got a btc deposit.
# Store the bitcoin record in the DB
@view_config(route_name='btc_deposit', request_method='POST', renderer='json')
def btc_deposit(request):

    user = User.from_umid(request.matchdict['guid'])

    addr       = request.json_body['address']
    amount_btc = request.json_body['amount']
    txid       = request.json_body['transaction']['id']
    created_at = request.json_body['transaction']['created_at']
    txhash     = request.json_body['transaction']['hash']

    #try:
    usd_per_btc = Bitcoin.get_spot_price()
    #except BTCException as e:
    #    # unknown exchange rate?
    #    print('Could not get exchange rate for addr %s txhash %s; failing...' % (addr, txhash))
    #    return {}

    ret = "addr: %s, amount: %s, txid: %s, created_at: %s, txhash: %s, exchange = $%s/BTC"\
           % (addr, amount_btc, txid, created_at, txhash, usd_per_btc)
    datalayer.bitcoin_deposit(user, Decimal(amount_btc) * usd_per_btc, txhash, addr, amount_btc)
    print(ret)


@view_config(route_name='btc_check', request_method='GET', renderer='json')
def btc_check(request):
    try:
        deposit = BTCDeposit.from_address(request.matchdict['addr'])
        return {"event_id": deposit.event.id}
    except:
        return {}


@view_config(route_name='deposit_new', request_method='POST', renderer='json', permission='service')
def deposit_new(request):
    try:
        user = User.from_umid(request.POST['umid'])
        amount = Decimal(request.POST['amount'])

        if amount > 20.0:
            raise DepositException('Deposit amount of ${:,.2f} exceeds the limit'.format(amount))

        deposit = datalayer.deposit(user, amount)

        # Return a JSON blob of the transaction ID so the client can redirect to
        # the deposit success page
        return {'event_id': deposit['event'].id}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid user error. Please try again.', 'error')
        return {'redirect_url': '/'}

    except ValueError as e:
        return {'error': 'Error understanding deposit amount.'}

    except DepositException as e:
        return {'error': str(e)}

