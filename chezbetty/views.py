from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.view import view_config, forbidden_view_config

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('betty')

from sqlalchemy.sql import func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import NoResultFound

from .models import *
from .models.model import *
from .models import user as __user
from .models.user import User
from .models.item import Item
from .models.box import Box
from .models.transaction import Transaction, BTCDeposit, PurchaseLineItem
from .models.account import Account, VirtualAccount, CashAccount
from .models.event import Event
from .models.announcement import Announcement
from .models.btcdeposit import BtcPendingDeposit
from .models.pool import Pool

from .utility import user_password_reset
from .utility import send_email

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException
import binascii
import transaction

import traceback

class DepositException(Exception):
    pass


###
### Catch-all error page
###

@view_config(route_name='exception_view', renderer='templates/exception.jinja2')
def exception_view(request):
    return {}

@view_config(context=Exception)
def exception_view_handler(context, request):
    print('An unknown error occurred:')
    traceback.print_exc()
    return HTTPFound(location=request.route_url('exception_view'))


###
### HTML Pages
###

### No login needed

@view_config(route_name='lang')
def lang(request):
    code = request.matchdict['code']
    response = Response()
    response.set_cookie('_LOCALE_', value=code, max_age=15*60) # reset lang after 15min

    return HTTPFound(location='/', headers=response.headers)

@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    announcements = Announcement.all_enabled()
    for announcement in announcements:
        request.session.flash(announcement.announcement, 'info')

    # For the demo mode
    if 'demo' in request.cookies and request.cookies['demo'] == '1':
        admins = User.get_admins()
    else:
        admins = []

    return {'admins': admins}


@view_config(route_name='about', renderer='templates/about.jinja2')
def about(request):
    return {}


@view_config(route_name='items', renderer='templates/items.jinja2')
def items(request):
    items = DBSession.query(Item)\
                     .filter(Item.enabled==True)\
                     .filter(Item.in_stock>0)\
                     .order_by(Item.name).all()
    out_of_stock_items = DBSession.query(Item)\
                     .filter(Item.enabled==True)\
                     .filter(Item.in_stock==0)\
                     .order_by(Item.name).all()
    disabled_items = DBSession.query(Item)\
                     .filter(Item.enabled==False)\
                     .order_by(Item.name).all()
    return {'items': items,
            'out_of_stock_items': out_of_stock_items,
            'disabled_items': disabled_items}


@view_config(route_name='item_request', renderer='templates/item_request.jinja2')
def item_request(request):
    return {}


@view_config(route_name='shame', renderer='templates/shame.jinja2')
def users(request):
    users = DBSession.query(User)\
                     .filter(User.balance < -5)\
                     .order_by(User.balance).all()
    return {'users': users}


@view_config(route_name='umid_check',
             request_method='POST',
             renderer='json',
             permission='service')
def umid_check(request):
    try:
        User.from_umid(request.POST['umid'])
        return {'status': 'success'}
    except:
        return {'status': 'error'}



### Post mcard swipe

@view_config(route_name='purchase', renderer='templates/purchase.jinja2', permission='service')
def purchase(request):
    try:
        if len(request.matchdict['umid']) != 8:
            raise __user.InvalidUserException()

        with transaction.manager:
            user = User.from_umid(request.matchdict['umid'])
        user = DBSession.merge(user)
        if not user.enabled:
            request.session.flash(_(
                'user-not-enabled',
                default='User is not enabled. Please contact ${email}.',
                mapping={'email':request.registry.settings['chezbetty.email']},
                ), 'error')
            return HTTPFound(location=request.route_url('index'))

        # For Demo mode:
        items = DBSession.query(Item)\
                         .filter(Item.enabled == True)\
                         .order_by(Item.name)\
                         .limit(6).all()

        # Pre-populate cart if returning from undone transaction
        existing_items = ''
        if len(request.GET) != 0:
            for (item_id, quantity) in request.GET.items():
                item = Item.from_id(int(item_id))
                existing_items += render('templates/item_row.jinja2',
                    {'item': item, 'quantity': int(quantity)})

        # Figure out if any pools can be used to pay for this purchase
        pools = []
        for pool in Pool.all_by_owner(user, True):
            if pool.balance > (pool.credit_limit * -1):
                pools.append(pool)

        for pu in user.pools:
            if pu.pool.enabled and pu.pool.balance > (pu.pool.credit_limit * -1):
                pools.append(pu.pool)

        return {'user': user,
                'items': items,
                'existing_items': existing_items,
                'pools': pools}

    except __user.InvalidUserException as e:
        request.session.flash(_(
            'mcard-error',
            default='Failed to read M-Card. Please try swiping again.',
            ), 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='user', renderer='templates/user.jinja2', permission='service')
def user(request):
    try:
        user = User.from_umid(request.matchdict['umid'])
        if not user.enabled:
            request.session.flash('User not permitted to purchase items.', 'error')
            return HTTPFound(location=request.route_url('index'))

        transactions,count = limitable_request(
                request, user.get_transactions, limit=20, count=True)
        return {'user': user,
                'transactions': transactions,
                'transactions_count': count,
                }

    except __user.InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='deposit', renderer='templates/deposit.jinja2', permission='service')
def deposit(request):
    try:
        user = User.from_umid(request.matchdict['umid'])

        # Record the deposit limit so we can show the user
        if user.total_deposits > 10.0 and user.total_purchases > 10.0:
            user.deposit_limit = 100.0
        else:
            user.deposit_limit = 20.0

        try:
            auth_key = binascii.b2a_hex(open("/dev/urandom", "rb").read(32))[:-3].decode("ascii")
            btc_addr = Bitcoin.get_new_address(user.umid, auth_key)
            btc_html = render('templates/btc.jinja2', {'addr': btc_addr})

            e = BtcPendingDeposit(user, auth_key, btc_addr)
            DBSession.add(e)
            DBSession.flush()
        except BTCException as e:
            print('BTC error: %s' % str(e))
            btc_html = ""

        # Get pools the user can deposit to
        pools = Pool.all_accessable(user, True)

        return {'user' : user,
                'btc'  : btc_html, 
                'pools': pools}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='deposit_edit',
             renderer='templates/deposit_edit.jinja2',
             permission='service')
def deposit_edit(request):
    try:
        user = User.from_umid(request.matchdict['umid'])
        event = Event.from_id(request.matchdict['event_id'])

        if event.type != 'deposit' or event.transactions[0].type != 'cashdeposit':
            request.session.flash('Can only edit a cash deposit.', 'error')
            return HTTPFound(location=request.route_url('index'))

        # Get pools the user can deposit to
        pools = []
        for pool in Pool.all_by_owner(user, True):
            pools.append(pool)

        for pu in user.pools:
            if pu.pool.enabled:
                pools.append(pu.pool)

        return {'user': user,
                'old_event': event,
                'old_deposit': event.transactions[0], 
                'pools': pools}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error.', 'error')
        return HTTPFound(location=request.route_url('index'))



@view_config(route_name='event', permission='service')
def event(request):
    try:
        event = Event.from_id(request.matchdict['event_id'])
        transaction = event.transactions[0]
        user = User.from_id(event.user_id)

        # Choose which page to show based on the type of event
        if event.type == 'deposit':
            # View the deposit success page
            prev_balance = user.balance - transaction.amount

            if transaction.to_account_virt_id == user.id:
                account_type = 'user'
                pool = None
            else:
                account_type = 'pool'
                pool = Pool.from_id(transaction.to_account_virt_id)

            return render_to_response('templates/deposit_complete.jinja2',
                {'deposit': transaction,
                 'user': user,
                 'event': event,
                 'prev_balance': prev_balance, 
                 'account_type': account_type,
                 'pool': pool}, request)

        elif event.type == 'purchase':
            # View the purchase success page
            order = {'total': transaction.amount,
                     'discount': transaction.discount,
                     'items': []}
            for subtrans in transaction.subtransactions:
                item = {}
                item['name'] = subtrans.item.name
                item['quantity'] = subtrans.quantity
                item['price'] = subtrans.item.price
                item['total_price'] = subtrans.amount
                order['items'].append(item)

            if transaction.fr_account_virt_id == user.id:
                account_type = 'user'
                pool = None
            else:
                account_type = 'pool'
                pool = Pool.from_id(transaction.fr_account_virt_id)

            request.session.flash('Success! The purchase was added successfully', 'success')
            return render_to_response('templates/purchase_complete.jinja2',
                {'user': user,
                 'event': event,
                 'order': order,
                 'transaction': transaction,
                 'account_type': account_type,
                 'pool': pool}, request)

    except NoResultFound as e:
        # TODO: add generic failure page
        pass
    except Exception as e:
        if request.debug: raise(e)
        return HTTPFound(location=request.route_url('index'))


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
        if transaction.type not in ('cashdeposit', 'purchase'):
            request.session.flash('Error: Only deposits and purchases may be undone.', 'error')
            return HTTPFound(location=request.route_url('index'))

        # Make sure that the user who is requesting the deposit was the one who
        # actually placed the deposit.
        try:
            user = User.from_id(event.user_id)
        except:
            request.session.flash('Error: Invalid user for transaction.', 'error')
            return HTTPFound(location=request.route_url('index'))

        if user.umid != request.matchdict['umid']:
            request.session.flash('Error: Transaction does not belong to specified user', 'error')
            return HTTPFound(location=request.route_url('user', umid=request.matchdict['umid']))

    # If the checks pass, actually revert the transaction
    try:
        line_items = datalayer.undo_event(event, user)
        if event.type == 'deposit':
            request.session.flash('Deposit successfully undone.', 'success')
        elif event.type == 'purchase':
            request.session.flash('Purchase undone. Please edit it as needed.', 'success')
    except:
        request.session.flash('Error: Failed to undo transaction.', 'error')
        return HTTPFound(location=request.route_url('purchase', umid=user.umid))

    if event.type == 'deposit':
        return HTTPFound(location=request.route_url('user', umid=user.umid))
    elif event.type == 'purchase':
        return HTTPFound(location=request.route_url('purchase', umid=user.umid, _query=line_items))
    else:
        assert(False and "Should not be able to get here?")


###
### JSON Requests
###

@view_config(route_name='item', renderer='json', permission='service')
def item(request):
    try:
        item = Item.from_barcode(request.matchdict['barcode'])
    except:
        # Could not find the item. Check to see if the user scanned a box
        # instead. This could lead to two cases: a) the box only has 1 item in it
        # in which case we just add that item to the cart. This likely occurred
        # because the individual items do not have barcodes so we just use
        # the box. b) The box has multiple items in it in which case we throw
        # an error for now.
        try:
            box = Box.from_barcode(request.matchdict['barcode'])
            if box.subitem_number == 1:
                item = box.items[0].item
            else:
                return {'status': 'scanned_box_with_multiple_items'}
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

@view_config(route_name='item_request_new', request_method='POST')
def item_request_new(request):
    try:
        request_text = request.POST['request']
        if len(request_text) < 5:
            raise ValueError()

        datalayer.new_request(None, request.POST['request'])

        request.session.flash('Request added successfully', 'success')
        return HTTPFound(location=request.route_url('index'))

    except ValueError:
        request.session.flash('If you are making a request, it should probably contain some characters.', 'error')
        return HTTPFound(location=request.route_url('item_request'))

    except:
        request.session.flash('Error adding request.', 'error')
        return HTTPFound(location=request.route_url('index'))

@view_config(route_name='item_request_by_id')
def item_request_by_id(request):
    item = Item.from_id(request.matchdict['id'])
    datalayer.new_request(None, item.name)
    request.session.flash('Request for {} added successfully'.format(item.name), 'success')
    return HTTPFound(location=request.route_url('index'))

@view_config(route_name='purchase_new',
             request_method='POST',
             renderer='json',
             permission='service')
def purchase_new(request):
    try:
        user = User.from_umid(request.POST['umid'])

        ignored_keys = ['umid', 'account', 'pool_id']

        # Bundle all purchase items
        items = {}
        for item_id,quantity in request.POST.items():
            if item_id in ignored_keys:
                continue
            item = Item.from_id(int(item_id))
            items[item] = int(quantity)

        # What should pay for this?
        # Note: should do a bunch of checking to make sure all of this
        # is kosher. But given our locked down single terminal, we're just
        # going to skip all of that.
        if request.POST['account'] == 'user':
            purchase = datalayer.purchase(user, user, items)
        elif request.POST['account'] == 'pool':
            pool = Pool.from_id(int(request.POST['pool_id']))
            purchase = datalayer.purchase(user, pool, items)

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

    user = User.from_umid(request.matchdict['umid'])
    auth_key = request.matchdict['auth_key']

    addr       = request.json_body['address']
    amount_btc = request.json_body['amount']
    txid       = request.json_body['transaction']['id']
    created_at = request.json_body['transaction']['created_at']
    txhash     = request.json_body['transaction']['hash']

    try:
        pending = BtcPendingDeposit.from_auth_key(auth_key)
    except NoResultFound as e:
        print("No result for auth_key %s" % auth_key)
        return {}


    if (pending.user_id != user.id or pending.address != addr):
        print("Mismatch of BtcPendingDeposit userid or address: (%d/%d), (%s/%s)" % (pending.user_id, user.id, pending.address, addr))
        return {}

    #try:
    usd_per_btc = Bitcoin.get_spot_price()
    #except BTCException as e:
    #    # unknown exchange rate?
    #    print('Could not get exchange rate for addr %s txhash %s; failing...' % (addr, txhash))
    #    return {}

    amount_usd = Decimal(amount_btc) * usd_per_btc

    # round down to nearest cent
    amount_usd = Decimal(int(amount_usd*100))/Decimal(100)

    ret = "addr: %s, amount: %s, txid: %s, created_at: %s, txhash: %s, exchange = $%s/BTC"\
           % (addr, amount_btc, txid, created_at, txhash, usd_per_btc)
    datalayer.bitcoin_deposit(user, amount_usd, txhash, addr, amount_btc)
    print(ret)

    return {}


@view_config(route_name='btc_check', request_method='GET', renderer='json')
def btc_check(request):
    try:
        deposit = BTCDeposit.from_address(request.matchdict['addr'])
        return {"event_id": deposit.event.id}
    except:
        return {}


@view_config(route_name='deposit_emailinfo',
             renderer='json',
             permission='service')
def deposit_emailinfo(request):
    try:
        user = User.from_id(int(request.matchdict['user_id']))
        if not user.has_password:
            return deposit_password_create(request)
        send_email(TO=user.uniqname+'@umich.edu',
                   SUBJECT='Chez Betty Credit Card Instructions',
                   body=render('templates/email_userinfo.jinja2', {'user': user}))
        return {'status': 'success',
                'msg': 'Instructions emailed to {}@umich.edu.'.format(user.uniqname)}
    except NoResultFound:
        return {'status': 'error',
                'msg': 'Could not find user.'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error',
                'msg': 'Error.'}


@view_config(route_name='deposit_password_create',
             renderer='json',
             permission='service')
def deposit_password_create(request):
    try:
        user = User.from_id(int(request.matchdict['user_id']))
        if user.has_password:
            return {'status': 'error',
                    'msg': 'Error: User already has password.'}
        user_password_reset(user)
        return {'status': 'success',
                'msg': 'Password set and emailed to {}@umich.edu.'.format(user.uniqname)}
    except NoResultFound:
        return {'status': 'error',
                'msg': 'Could not find user.'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error',
                'msg': 'Error.'}

@view_config(route_name='deposit_password_reset',
        renderer='json',
        permission='service')
def deposit_password_reset(request):
    try:
        user = User.from_id(int(request.matchdict['user_id']))
        user_password_reset(user)
        return {'status': 'success',
                'msg': 'Password set and emailed to {}@umich.edu.'.format(user.uniqname)}
    except NoResultFound:
        return {'status': 'error',
                'msg': 'Could not find user.'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error',
                'msg': 'Error.'}

@view_config(route_name='deposit_new',
             request_method='POST',
             renderer='json',
             permission='service')
def deposit_new(request):
    try:
        user = User.from_umid(request.POST['umid'])
        amount = Decimal(request.POST['amount'])
        account = request.POST['account']

        # Check if the deposit amount is too great.
        # This if block could be tighter, but this is easier to understand
        if amount > 100.0:
            # Anything above 100 is blocked
            raise DepositException('Deposit amount of ${:,.2f} exceeds the limit'.format(amount))

        if amount < 100.0 and amount > 20.0 and (user.total_deposits < 10.0 or user.total_purchases < 10.0):
            # If the deposit is between 20 and 100 and the user hasn't done much
            # with betty. Block the deposit. We do allow deposits up to 100 for
            # customers that have shown they know how to scan/purchase and
            # deposit
            raise DepositException('Deposit amount of ${:,.2f} exceeds the limit'.format(amount))

        if amount <= 0.0:
            raise DepositException('Deposit amount must be greater than $0.00')

        if account == 'user':
            deposit = datalayer.deposit(user, user, amount)
        elif account == 'pool':
            deposit = datalayer.deposit(user, Pool.from_id(request.POST['pool_id']), amount)

        # Return a JSON blob of the transaction ID so the client can redirect to
        # the deposit success page
        return {'event_id': deposit['event'].id}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid user error. Please try again.', 'error')
        return {'error': 'Error finding user.',
                'redirect_url': '/'}

    except ValueError as e:
        return {'error': 'Error understanding deposit amount.'}

    except DepositException as e:
        return {'error': str(e)}


@view_config(route_name='deposit_edit_submit',
             request_method='POST',
             renderer='json',
             permission='service')
def deposit_edit_submit(request):
    try:
        user = User.from_umid(request.POST['umid'])
        amount = Decimal(request.POST['amount'])
        old_event = Event.from_id(request.POST['old_event_id'])

        if old_event.type != 'deposit' or \
           old_event.transactions[0].type != 'cashdeposit' or \
           (old_event.transactions[0].to_account_virt_id != user.id and \
            old_event.user_id != user.id):
           # Something went wrong, can't undo this deposit
           raise DepositException('Cannot undo that deposit')

        new_deposit = deposit_new(request)

        if 'error' in new_deposit and new_deposit['error'] != 'success':
            # Error occurred, do not delete old event
            return new_deposit

        # Now undo old deposit
        datalayer.undo_event(old_event, user)

        return new_deposit

    except __user.InvalidUserException as e:
        request.session.flash('Invalid user error. Please try again.', 'error')
        return {'redirect_url': '/'}

    except DepositException as e:
        return {'error': str(e)}

    except Exception as e:
        if request.debug: raise(e)
        return {'error': 'Error.'}

