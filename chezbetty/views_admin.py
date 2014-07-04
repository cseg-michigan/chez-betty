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
from .models import event as __event

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException

import threading
demo_lock = threading.Lock()
demo = False

###
### Global Attributes (passed to every template)
###   - n.b. This really is global, it will pick up views routes too
###
@subscriber(BeforeRender)
def add_global(event):
    assert(event.rendering_val.get('demo') is None)
    with demo_lock:
        event.rendering_val['demo'] = demo

###
### Admin
###

@view_config(route_name='admin_index', renderer='templates/admin/index.jinja2', permission='manage')
def admin_index(request):
    events          = DBSession.query(Event)\
                               .order_by(desc(Event.id))\
                               .limit(10).all()
    items_low_stock = DBSession.query(Item)\
                               .filter(Item.enabled == True)\
                               .filter(Item.in_stock < 10)\
                               .order_by(Item.in_stock)\
                               .limit(5).all()
    users_shame     = DBSession.query(User)\
                               .filter(User.balance < 0)\
                               .order_by(User.balance)\
                               .limit(5).all()
    users_balance   = DBSession.query(func.sum(User.balance).label("total_balance")).one()
    bsi             = DBSession.query(func.sum(PurchaseLineItem.quantity).label('quantity'), Item.name)\
                               .join(Item)\
                               .join(Transaction)\
                               .filter(Transaction.type=='purchase')\
                               .group_by(Item.id)\
                               .order_by(desc('quantity'))\
                               .limit(5).all()
    inventory       = DBSession.query(func.sum(Item.in_stock * Item.wholesale).label("wholesale"),
                                      func.sum(Item.in_stock * Item.price).label("price")).one()

    chezbetty       = VirtualAccount.from_name("chezbetty")
    cashbox         = CashAccount.from_name("cashbox")
    btcbox          = CashAccount.from_name("btcbox")
    chezbetty_cash  = CashAccount.from_name("chezbetty")

    cashbox_lost    = Transaction.get_balance("lost", account.get_cash_account("cashbox"))
    cashbox_found   = Transaction.get_balance("found", account.get_cash_account("cashbox"))
    btcbox_lost     = Transaction.get_balance("lost", account.get_cash_account("btcbox"))
    btcbox_found    = Transaction.get_balance("found", account.get_cash_account("btcbox"))
    chezbetty_lost  = Transaction.get_balance("lost", account.get_cash_account("chezbetty"))
    chezbetty_found = Transaction.get_balance("found", account.get_cash_account("chezbetty"))
    restock         = Transaction.get_balance("restock", account.get_cash_account("chezbetty"))
    donation        = Transaction.get_balance("donation", account.get_cash_account("chezbetty"))
    withdrawal      = Transaction.get_balance("withdrawal", account.get_cash_account("chezbetty"))

    try:
        btc_balance = Bitcoin.get_balance()
        btc = {"btc": btc_balance,
               "mbtc": round(btc_balance*1000, 2),
               "usd": btc_balance * Bitcoin.get_spot_price()}
    except BTCException:
        btc = {"btc": None,
               "mbtc": None,
               "usd": None}

    return dict(events=events,
                items_low_stock=items_low_stock,
                users_shame=users_shame,
                users_balance=users_balance,
                cashbox=cashbox,
                btcbox=btcbox,
                chezbetty_cash=chezbetty_cash,
                chezbetty=chezbetty,
                btc_balance=btc,
                cashbox_lost=cashbox_lost,
                cashbox_found=cashbox_found,
                btcbox_lost=btcbox_lost,
                btcbox_found=btcbox_found,
                chezbetty_lost=chezbetty_lost,
                chezbetty_found=chezbetty_found,
                restock=restock,
                donation=donation,
                withdrawal=withdrawal,
                inventory=inventory,
                best_selling_items=bsi)

@view_config(route_name='admin_demo', renderer='json')
def admin_demo(request):
    global demo_lock
    global demo
    with demo_lock:
        if request.matchdict['state'].lower() == 'true':
            demo = True
        else:
            demo = False
        return {}

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
            price = 0
            enabled = False

            # Parse out the important fields looking for errors
            try:
                name = request.POST['item-name-{}'.format(id)]
                barcode = request.POST['item-barcode-{}'.format(id)]

                # Check that name and barcode are not blank. If name is blank
                # treat this as an empty row and skip. If barcode is blank
                # we will get a database error so send that back to the user.
                if name == '':
                    continue
                if barcode == '':
                    request.session.flash('Error adding item "{}". Barcode cannot be blank.'.format(name), 'error')
                    error_items.append({
                        'name': name, 'barcode': ''
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
                            'barcode' : request.POST['item-barcode-{}'.format(id)]
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


@view_config(route_name='admin_cash_donation',
        renderer='templates/admin/cash_donation.jinja2', permission='manage')
def admin_cash_donation(request):
    return {}


@view_config(route_name='admin_cash_donation_submit', request_method='POST',
        permission='manage')
def admin_cash_donation_submit(request):
    try:
        amount = Decimal(request.POST['amount'])
        datalayer.add_donation(amount, request.POST['notes'], request.user)

        request.session.flash('Donation recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_index'))

    except ValueError:
        request.session.flash('Error: Bad value for donation amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_donation'))
    except __event.NotesMissingException:
        request.session.flash('Error: Must include a donation reason', 'error')
        return HTTPFound(location=request.route_url('admin_cash_donation'))
    except:
        request.session.flash('Error: Unable to add donation', 'error')
        return HTTPFound(location=request.route_url('admin_cash_donation'))


@view_config(route_name='admin_cash_withdrawal',
        renderer='templates/admin/cash_withdrawal.jinja2', permission='manage')
def admin_cash_withdrawal(request):
    return {}


@view_config(route_name='admin_cash_withdrawal_submit', request_method='POST',
        permission='manage')
def admin_cash_withdrawal_submit(request):
    try:
        amount = Decimal(request.POST['amount'])
        datalayer.add_withdrawal(amount, request.POST['notes'], request.user)

        request.session.flash('Withdrawal recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_index'))

    except ValueError:
        request.session.flash('Error: Bad value for withdrawal amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_withdrawal'))
    except __event.NotesMissingException:
        request.session.flash('Error: Must include a withdrawal reason', 'error')
        return HTTPFound(location=request.route_url('admin_cash_withdrawal'))
    except:
        request.session.flash('Error: Unable to add withdrawal', 'error')
        return HTTPFound(location=request.route_url('admin_cash_withdrawal'))


@view_config(route_name='admin_cash_adjustment',
        renderer='templates/admin/cash_adjustment.jinja2', permission='manage')
def admin_cash_adjustment(request):
    return {}


@view_config(route_name='admin_cash_adjustment_submit', request_method='POST',
        permission='manage')
def admin_cash_adjustment_submit(request):
    try:
        amount = Decimal(request.POST['amount'])
        datalayer.reconcile_misc(amount, request.POST['notes'], request.user)

        request.session.flash('Adjustment recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_index'))

    except ValueError:
        request.session.flash('Error: Bad value for adjustment amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_adjustment'))
    except __event.NotesMissingException:
        request.session.flash('Error: Must include a adjustment reason', 'error')
        return HTTPFound(location=request.route_url('admin_cash_adjustment'))
    except:
        request.session.flash('Error: Unable to add adjustment', 'error')
        return HTTPFound(location=request.route_url('admin_cash_adjustment'))


@view_config(route_name='admin_transactions',
        renderer='templates/admin/transactions.jinja2', permission='admin')
def admin_transactions(request):
    events = DBSession.query(Event).order_by(desc(Event.id)).all()
    return {'events':events}


@view_config(route_name='admin_event',
        renderer='templates/admin/event.jinja2', permission='admin')
def admin_event(request):
    try:
        e = Event.from_id(int(request.matchdict['event_id']))
        return {'event': e}
    except ValueError:
        request.session.flash('Invalid event ID', 'error')
        return HTTPFound(location=request.route_url('admin_transactions'))
    except:
        request.session.flash('Could not find event ID#{}'\
            .format(request.matchdict['event_id']), 'error')
        return HTTPFound(location=request.route_url('admin_transactions'))


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

