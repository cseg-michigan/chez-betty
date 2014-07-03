from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.view import view_config, forbidden_view_config
from pyramid.httpexceptions import HTTPFound

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

import qrcode
import qrcode.image.svg

from .btc import BTCException
from decimal import Decimal

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

###
### Utility Function
###

def string_to_qrcode(s):
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(s, image_factory=factory, box_size=14,
        version=4,
        border=0)
    img.save('/dev/null')   # This is needed, I swear.
    return ET.tostring(img._img)

from .btc import Bitcoin

import json

import qrcode
import qrcode.image.svg

class DepositException(Exception):
    pass

###
### HTML Pages
###

@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    return {}

@view_config(route_name='about', renderer='templates/about.jinja2')
def about(request):
    return {}

@view_config(route_name='purchase', renderer='templates/purchase.jinja2', permission='service')
def purchase(request):
    try:
        if len(request.matchdict['umid']) != 8:
            raise __user.InvalidUserException()

        user = User.from_umid(request.matchdict['umid'])
        if not user.enabled:
            request.session.flash('User is not enabled. Please contact chezbetty@umich.edu.', 'error')
            return HTTPFound(location=request.route_url('index'))
        purchase_info = render('templates/user_info.jinja2', {'user': user,
                                                              'page': 'purchase'})
        return {'purchase_info_block': purchase_info}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid M-Card swipe. Please try again.', 'error')
        return HTTPFound(location=request.route_url('index'))

@view_config(route_name='items', renderer='templates/items.jinja2')
def items(request):
    items = DBSession.query(Item).filter(Item.enabled==True).order_by(Item.name).all()
    return {'items': items}

@view_config(route_name='shame', renderer='templates/shame.jinja2')
def users(request):
    users = DBSession.query(User).filter(User.balance < -5).order_by(User.balance).all()
    return {'users': users}

@view_config(route_name='user', renderer='templates/user.jinja2', permission='service')
def user(request):
    try:
        user = User.from_umid(request.matchdict['umid'])
        if not user.enabled:
            request.session.flash('User not permitted to purchase items.', 'error')
            return HTTPFound(location=request.route_url('index'))

        user_info_html = render('templates/user_info.jinja2',
            {'user': user, 'page': 'account'})

        tx_tuples = []  # list of (transaction, btc_tx_url_image)s
        for tx_idx in range(len(user.transactions)):
            tx = user.transactions[tx_idx]
            img = ''
            if tx.type == "btcdeposit":
                svg_html = string_to_qrcode('https://blockchain.info/tx/%s' % tx.btctransaction)
                img = svg_html.decode('utf-8')
            tx_tuples.append((tx, img))

        return {'user': user,
                'user_info_block': user_info_html,
                'transactions': tx_tuples}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='deposit', renderer='templates/deposit.jinja2', permission='service')
def deposit(request):
    try:
        user = User.from_umid(request.matchdict['umid'])

        user_info_html = render('templates/user_info.jinja2', {'user': user,
                                                               'page': 'deposit'})
        keypad_html = render('templates/keypad.jinja2', {})

        try:
            btc_addr = Bitcoin.get_new_address(user.umid)
            btc_html = render('templates/btc.jinja2', {'addr': btc_addr})
        except BTCException as e:
            btc_html = ""

        return {'user_info_block': user_info_html, 'keypad': keypad_html, 'btc' : btc_html}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='event', permission='service')
def event(request):

    try:
        event = DBSession.query(Event) \
            .filter(Event.id==int(request.matchdict['event_id'])).one()
        transaction = event.transaction[0]

        # Choose which page to show based on the type of event
        if event.type == 'deposit':
            # View the deposit success page

            user = DBSession.query(User) \
                .filter(User.id==transaction.to_account_virt_id).one()

            user_info_html = render('templates/user_info.jinja2',
                {'user': user, 'page': 'deposit'})

            btcimg = ""
            txhash = ""
            amount_btc = 0.0
            if transaction.type == 'btcdeposit':
                txhash = transaction.btctransaction
                btcimg = string_to_qrcode('https://blockchain.info/tx/%s' % txhash).decode('utf-8')
                amount_btc = transaction.amount_btc

            deposit = {'transaction_id': transaction.id,
                       'type': transaction.type,
                       'umid': user.umid,
                       'prev': user.balance - transaction.amount,
                       'amount': transaction.amount,
                       'btcamount' : amount_btc,
                       'btcimg' : btcimg,
                       'txhash' : txhash,
                       'new': user.balance,
                       'event_id': event.id}
            return render_to_response('templates/deposit_complete.jinja2',
                {'deposit': deposit, 'user_info_block': user_info_html}, request)

        elif event.type == 'purchase':
            # View the purchase success page
            user = DBSession.query(User) \
                .filter(User.id==transaction.fr_account_virt_id).one()

            user_info_html = render('templates/user_info.jinja2',
                {'user': user, 'page': 'purchase'})

            order = {'total': transaction.amount,
                     'items': []}
            for subtrans in transaction.subtransactions:
                item = {}
                item['name'] = subtrans.item.name
                item['quantity'] = subtrans.quantity
                item['price'] = subtrans.item.price
                item['total_price'] = subtrans.amount
                order['items'].append(item)

            # TODO: get the products for all this
            return render_to_response('templates/purchase_complete.jinja2',
                {'user_info_block': user_info_html,
                 'order': order}, request)

    except NoResultFound as e:
        # TODO: add generic failure page
        pass

@view_config(route_name='event_undo', permission='service')
def event_undo(request):
    # Lookup the transaction that the user wants to undo
    #try:
    event = Event.from_id(request.matchdict['event_id'])
    transaction = event.transaction[0]
    #except:
    #    request.session.flash('Error: Could not find transaction to undo.', 'error')
    #    return HTTPFound(location=request.route_url('index'))

    # Make sure transaction is a deposit, the only one the user is allowed
    # to undo
    if transaction.type != 'deposit':
        request.session.flash('Error: Only deposits may be undone.', 'error')
        return HTTPFound(location=request.route_url('index'))

    # Make sure that the user who is requesting the deposit was the one who
    # actually placed the deposit.
    try:
        user = DBSession.query(User) \
            .filter(User.id==transaction.to_account_virt_id).one()
    except:
        request.session.flash('Error: Invalid user for transaction.', 'error')
        return HTTPFound(location=request.route_url('index'))
    if user.umid != request.matchdict['umid']:
        request.session.flash('Error: Transaction does not belong to specified user', 'error')
        return HTTPFound(location=request.route_url('user', umid=request.matchdict['umid']))

    # If the checks pass, actually revert the transaction
    #try:
    datalayer.undo_event(event)
    #    request.session.flash('Transaction successfully reverted.', 'success')
    #except:
    #    request.session.flash('Error: Failed to undo transaction.', 'error')
    return HTTPFound(location=request.route_url('user', umid=user.umid))

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
            item = DBSession.query(Item).filter(Item.id == int(item_id)).one()
            items[item] = int(quantity)

        # Commit the purchase
        purchase = datalayer.purchase(user, items)

        # Return the committed transaction ID
        return {'event_id': purchase.id}

    except __user.InvalidUserException as e:
        request.session.flash('Invalid user error. Please try again.', 'error')
        return {'redirect_url': '/'}

    except ValueError as e:
        return {'error': 'Unable to parse Item ID or quantity'}

    except NoResultFound as e:
        # Could not find an item
        return {'error': 'Unable to identify an item.'}


@view_config(route_name='btc_deposit', request_method='POST', renderer='json')
def btc_deposit(request):

    user = User.from_umid(request.matchdict['guid'])

    addr = request.json_body['address']
    amount_btc = request.json_body['amount']
    txid = request.json_body['transaction']['id']
    created_at = request.json_body['transaction']['created_at']
    txhash = request.json_body['transaction']['hash']

    print("got a btc_deposit request...: %s" % request)

    try:
        usd_per_btc = Bitcoin.get_spot_price()
    except BTCException as e:
        # unknown exchange rate?
        print('Could not get exchange rate for addr %s txhash %s; failing...' % (addr, txhash))
        return {}

    ret = "addr: %s, amount: %s, txid: %s, created_at: %s, txhash: %s, exchange = $%s/BTC" % (addr, amount_btc, txid, created_at, txhash, usd_per_btc)
    datalayer.bitcoin_deposit(user, Decimal(amount_btc) * usd_per_btc, txhash, addr, amount_btc)
    print(ret)
    #return ret

@view_config(route_name='btc_check', request_method='GET', renderer='json')
def btc_check(request):
    res = 0

    row = DBSession.query(BTCDeposit).filter(BTCDeposit.address==request.matchdict['addr']).first()
    if row is not None:
        res = row.id
    return {"result" : res}


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




###
### Admin
###

@view_config(route_name='admin_index', renderer='templates/admin/index.jinja2', permission='manage')
def admin_index(request):
    events = DBSession.query(Event).order_by(desc(Event.id)).limit(10).all()
    #ct = DBSession.query(Transaction).order_by(desc(CashTransaction.id)).limit(10).all()
    items = DBSession.query(Item).filter(Item.enabled == True).filter(Item.in_stock < 10).order_by(Item.in_stock).limit(5).all()
    users = DBSession.query(User).filter(User.balance < 0).order_by(User.balance).limit(5).all()
    users_balance = DBSession.query(func.sum(User.balance).label("total_balance")).one()[0]
    chezbetty = DBSession.query(VirtualAccount).filter(Account.name == "chezbetty").one()
    cashbox = DBSession.query(CashAccount).filter(CashAccount.name=="cashbox").one()
    chezbetty_cash = DBSession.query(CashAccount).filter(CashAccount.name=="chezbetty").one()
    #try:
    #    btc_balance = Bitcoin.get_balance()
    #except:
    btc_balance = -1
    #usd_btc_balance = btc_balance * Bitcoin.get_spot_price()
    usd_btc_balance = -1

    class Object(object):
        pass

    inventory = Object()
    inventory.wholesale = DBSession.query(func.sum(Item.in_stock * Item.wholesale)).one()[0]
    inventory.price = DBSession.query(func.sum(Item.in_stock * Item.price)).one()[0]

    bsi = DBSession.query(func.sum(PurchaseLineItem.quantity).label('quantity'), Item.name)\
                   .join(Item)\
                   .join(Transaction)\
                   .filter(Transaction.type=='purchase')\
                   .group_by(Item.id)\
                   .order_by(desc('quantity'))\
                   .limit(5).all()

    sums = Object()
    sums.virtual = chezbetty.balance + users_balance
    sums.cash = chezbetty_cash.balance + cashbox.balance

    return dict(events=events, items=items, users=users,
                    users_total_balance=users_balance,
                    cashbox=cashbox,
                    chezbetty_cash=chezbetty_cash,
                    chezbetty=chezbetty,
                    btc_balance={"btc": btc_balance, "mbtc" : round(btc_balance*1000, 2), "usd": usd_btc_balance},
                    sums=sums,
                    inventory=inventory,
                    best_selling_items=bsi
           )

@view_config(route_name='admin_item_barcode_json', renderer='json')
def admin_item_barcode_json(request):
    try:
        item = Item.from_barcode(request.matchdict['barcode'])
    except:
        return {'status': 'unknown_barcode'}
    if item.enabled:
        status = 'success'
    else:
        status = 'disabled'
    item_restock_html = render('templates/admin/restock_row.jinja2', {'item': item})
    return {'status' : status, 'data' : item_restock_html, 'id' : item.id}

@view_config(route_name='admin_restock', renderer='templates/admin/restock.jinja2', permission='manage')
def admin_restock(request):
    return {}

@view_config(route_name='admin_restock_submit', request_method='POST')
def admin_restock_submit(request):
    i = iter(request.POST)
    items = {}
    for salestax,quantity,cost in zip(i,i,i):
        if not (quantity.split('-')[2] == cost.split('-')[2] == salestax.split('-')[2]):
            request.session.flash('Error: Malformed POST. Misaligned IDs.', 'error')
            DBSession.rollback()
            return HTTPFound(location=request.route_url('admin_restock'))
        try:
            item = Item.from_id(int(quantity.split('-')[2]))
        except:
            request.session.flash('No item with id {} found. Skipped.'.\
                    format(int(quantity.split('-')[2])), 'error')
            continue
        try:
            quantity = int(request.POST[quantity])
            if '/' in request.POST[cost]:
                dividend, divisor = map(float, request.POST[cost].split('/'))
                cost = dividend / divisor
            else:
                cost = Decimal(request.POST[cost])
        except ValueError:
            request.session.flash('Non-numeric value for {}. Skipped.'.\
                    format(item.name), 'error')
            continue
        except ZeroDivisionError:
            request.session.flash('Really? Dividing by 0? Item {} skipped.'.\
                    format(item.name), 'error')
            continue
        salestax = request.POST[salestax] == 'on'
        if salestax:
            wholesale = (cost * 1.06) / quantity
        else:
            wholesale = cost / quantity

        item.wholesale = round(wholesale, 4)

        if item.price < item.wholesale:
            item.price = round(item.wholesale * Decimal(1.15), 2)

        items[item] = quantity

    datalayer.restock(items, request.user)
    request.session.flash('Restock complete.', 'success')
    return HTTPFound(location=request.route_url('admin_edit_items'))

@view_config(route_name='admin_add_items', renderer='templates/admin/add_items.jinja2', permission='manage')
def admin_add_items(request):
    if len(request.GET) == 0:
        return {'items' : {'count': 1,
                'name-0': '',
                'barcode-0': '',
                'price-0': '',
                }}
    else:
        d = {'items' : request.GET}
        return d

@view_config(route_name='admin_add_items_submit', request_method='POST', permission='manage')
def admin_add_items_submit(request):
    count = 0
    error_items = []

    # Iterate all the POST keys and find the ones that are item names
    for key in request.POST:
        if 'item-name-' in key:
            id = int(key.split('-')[2])
            stock = 0
            wholesale = 0
            enabled = False

            # Parse out the important fields looking for errors
            try:
                name = request.POST['item-name-{}'.format(id)]
                barcode = request.POST['item-barcode-{}'.format(id)]
                try:
                    price = float(request.POST['item-price-{}'.format(id)])
                except:
                    price = 0

                # Check that name and barcode are not blank. If name is blank
                # treat this as an empty row and skip. If barcode is blank
                # we will get a database error so send that back to the user.
                if name == '':
                    continue
                if barcode == '':
                    request.session.flash('Error adding item "{}". Barcode cannot be blank.'.format(name), 'error')
                    error_items.append({
                        'name': name, 'barcode': '', 'price': price,
                    })
                    continue

                # Add the item to the DB
                item = Item(name, barcode, price, wholesale, stock, enabled)
                DBSession.add(item)
                DBSession.flush()
                count += 1
            except:
                if len(name):
                    error_items.append({
                            'name' : request.POST['item-name-{}'.format(id)],
                            'barcode' : request.POST['item-barcode-{}'.format(id)],
                            'price' : request.POST['item-price-{}'.format(id)],
                            })
                    request.session.flash('Error adding item: {}. Most likely a duplicate barcode.'.\
                                    format(name), 'error')
                # Otherwise this was probably a blank row; ignore.
    if count:
        request.session.flash('{} item{} added successfully.'.format(count, ['s',''][count==1]), 'success')
    else:
        request.session.flash('No items added.', 'error')
    if len(error_items):
        flat = {}
        e_count = 0
        for err in error_items:
            for k,v in err.items():
                flat['{}-{}'.format(k, e_count)] = v
            e_count += 1
        flat['count'] = len(error_items)
        return HTTPFound(location=request.route_url('admin_add_items', _query=flat))
    else:
        return HTTPFound(location=request.route_url('admin_edit_items'))

@view_config(route_name='admin_edit_items', renderer='templates/admin/edit_items.jinja2', permission='manage')
def admin_edit_items(request):
    items_active = DBSession.query(Item).filter_by(enabled=True).order_by(Item.name).all()
    items_inactive = DBSession.query(Item).filter_by(enabled=False).order_by(Item.name).all()
    items = items_active + items_inactive
    return {'items': items}

@view_config(route_name='admin_edit_items_submit', request_method='POST', permission='manage')
def admin_edit_items_submit(request):
    updated = set()
    for key in request.POST:
        try:
            item = Item.from_id(int(key.split('-')[2]))
        except:
            request.session.flash('No item with ID {}.  Skipped.'.format(key.split('-')[2]), 'error')
            continue
        name = item.name
        try:
            field = key.split('-')[1]
            if field == 'price':
                val = round(float(request.POST[key]), 2)
            elif field == 'wholesale':
                val = round(float(request.POST[key]), 4)
            else:
                val = request.POST[key]

            setattr(item, field, val)
            DBSession.flush()
        except:
            DBSession.rollback()
            request.session.flash('Error updating {} for {}.  Skipped.'.\
                    format(key.split('-')[1], name), 'error')
            continue
        updated.add(item.id)
    if len(updated):
        count = len(updated)
        #request.session.flash('{} item{} properties updated successfully.'.format(count, ['s',''][count==1]), 'success')
        request.session.flash('Items updated successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_edit_items'))

@view_config(route_name='admin_inventory', renderer='templates/admin/inventory.jinja2', permission='manage')
def admin_inventory(request):
    items = DBSession.query(Item).order_by(Item.name).all()
    return {'items': items}

@view_config(route_name='admin_inventory_submit', request_method='POST', permission='manage')
def admin_inventory_submit(request):
    items = {}
    for key in request.POST:
        item = Item.from_id(key.split('-')[2])
        try:
            items[item] = int(request.POST[key])
        except ValueError:
            pass
    t = datalayer.reconcile_items(items, request.user)
    request.session.flash('Inventory Reconciled', 'success')
    if t.amount < 0:
        request.session.flash('Chez Betty made ${:,.2f}'.format(-t.amount), 'success')
    elif t.amount == 0:
        request.session.flash('Chez Betty was spot on.', 'success')
    else:
        request.session.flash('Chez Betty lost ${:,.2f}. :('.format(t.amount), 'error')
    return HTTPFound(location=request.route_url('admin_inventory'))

@view_config(route_name='login', renderer='templates/login.jinja2')
@forbidden_view_config(renderer='templates/login.jinja2')
def login(request):
    login_url = request.resource_url(request.context, 'login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    message = login = password = ''
    if 'login' in request.params:
        login = request.params['login']
        password = request.params['password']
        user = DBSession.query(User).filter(User.uniqname == login).first()
        if user and not user.enabled:
            message = 'Login failed. User not allowed to login.'
        elif user and user.check_password(password):
            # successful login
            headers = remember(request, login)
            return HTTPFound(location=came_from, headers=headers)
        else:
            message = 'Login failed. Incorrect username or password.',

    return dict(
        message = message,
        url = request.application_url + '/login',
        came_from = came_from,
        login = login,
        password = password
    )


@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location=request.route_url('index'),
                     headers = headers)

@view_config(route_name='admin_edit_users', renderer='templates/admin/edit_users.jinja2')
def admin_edit_users(request):
    enabled_users = DBSession.query(User).filter_by(enabled=True).order_by(User.name).all()
    disabled_users = DBSession.query(User).filter_by(enabled=False).order_by(User.name).all()
    users = enabled_users + disabled_users
    roles = [('user', 'User'),
             ('serviceaccount', 'Service Account'),
             ('manager', 'Manager'),
             ('administrator', 'Administrator')]
    return {'users': users, 'roles': roles}

@view_config(route_name='admin_edit_users_submit',
        request_method='POST', permission='admin')
def admin_edit_users_submit(request):
    for key in request.POST:
        user = User.from_id(int(key.split('-')[2]))
        setattr(user, key.split('-')[1], request.POST[key])
    request.session.flash('Users updated successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_edit_users'))

@view_config(route_name='admin_edit_balance',
        renderer='templates/admin/edit_balance.jinja2')
def admin_edit_balance(request):
    users = DBSession.query(User).order_by(User.name).all()
    return {'users': users}

@view_config(route_name='admin_edit_balance_submit', request_method='POST',
        permission='admin')
def admin_edit_balance_submit(request):
    try:
        user = User.from_id(int(request.POST['user']))
    except:
        request.session.flash('Invalid user?', 'error')
        return HTTPFound(location=request.route_url('admin_edit_balance'))
    try:
        adjustment = Decimal(request.POST['amount'])
    except:
        request.session.flash('Invalid adjustment amount.', 'error')
        return HTTPFound(location=request.route_url('admin_edit_balance'))
    reason = request.POST['reason']
    datalayer.adjust_user_balance(user, adjustment, reason, request.user)
    request.session.flash('User account updated.', 'success')
    return HTTPFound(location=request.route_url('admin_edit_balance'))

@view_config(route_name='admin_cash_reconcile',
        renderer='templates/admin/cash_reconcile.jinja2', permission='manage')
def admin_cash_reconcile(request):
    return {}

@view_config(route_name='admin_cash_reconcile_submit', request_method='POST',
        permission='manage')
def admin_cash_reconcile_submit(request):
    try:
        amount = Decimal(request.POST['amount'])
    except ValueError:
        request.session.flash('Error: Bad value for cash box amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_reconcile'))

    expected_amount = datalayer.reconcile_cash(amount, request.user)

    request.session.flash('Cash box recorded successfully', 'success')
    return HTTPFound(location=request.route_url('admin_cash_reconcile_success',
        _query={'amount':amount, 'expected_amount':expected_amount}))

@view_config(route_name='admin_cash_reconcile_success',
        renderer='templates/admin/cash_reconcile_complete.jinja2', permission='manage')
def admin_cash_reconcile_success(request):
    deposit = float(request.GET['amount'])
    expected = float(request.GET['expected_amount'])
    difference = deposit - expected
    return {'cash': {'deposit': deposit, 'expected': expected, 'difference': difference}}

@view_config(route_name='admin_transactions',
        renderer='templates/admin/transactions.jinja2', permission='admin')
def admin_transactions(request):
    transactions = DBSession.query(Transaction).order_by(desc(Transaction.id)).all()
    return {'transactions':transactions}

@view_config(route_name='admin_view_transaction',
        renderer='templates/admin/view_transaction.jinja2', permission='admin')
def admin_view_transaction(request):
    id = int(request.matchdict['id'])
    t = DBSession.query(Transaction).filter(Transaction.id == id).first()
    if not t:
        request.session.flash('Invalid transaction ID supplied', 'error')
        return HTTPFound(location=request.route_url('admin_transactions'))
    return dict(t=t)

@view_config(route_name='admin_edit_password',
        renderer='templates/admin/edit_password.jinja2', permission='manage')
def admin_edit_password(request):
    return {}

@view_config(route_name='admin_edit_password_submit', request_method='POST',
        permission='manage')
def admin_edit_password_submit(request):
    pwd0 = request.POST['edit-password-0']
    pwd1 = request.POST['edit-password-1']
    if pwd0 != pwd1:
        request.session.flash('Error: Passwords do not match', 'error')
        return HTTPFound(location=request.route_url('admin_edit_password'))
    request.user.password = pwd0
    request.session.flash('Password changed successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_index'))
    # check that changing password for actually logged in user

@view_config(route_name='admin_cash_transactions', permission='admin', renderer="templates/admin/cash_transactions.jinja2")
def admin_cash_transactions(request):
    accounts = DBSession.query(CashAccount).order_by(CashAccount.name).all()
    ct = DBSession.query(CashTransaction).order_by(desc(CashTransaction.id)).all()
    return dict(accounts=accounts, ct=ct)
