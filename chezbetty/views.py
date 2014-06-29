from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import NoResultFound

from .models import *
from .models.model import *
from .models.user import User, InvalidUserException
from .models.item import Item
from .models.transaction import Transaction

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer

from pprint import pprint

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

@view_config(route_name='purchase', renderer='templates/purchase.jinja2')
def purchase(request):
    try:
        if len(request.matchdict['umid']) != 8:
            raise InvalidUserException

        user = User.from_umid(request.matchdict['umid'])
        purchase_info = render('templates/user_info.jinja2', {'user': user,
                                                              'page': 'purchase'})
        return {'purchase_info_block': purchase_info}

    except InvalidUserException as e:
        request.session.flash("Invalid M-Card swipe. Please try again.", "error")
        return HTTPFound(location=request.route_url('index'))

@view_config(route_name='items', renderer='templates/items.jinja2')
def items(request):
    items = DBSession.query(Item).all()
    return {'items': items}

@view_config(route_name='users', renderer='templates/users.jinja2')
def users(request):
    users = DBSession.query(User).all()
    return {'users': users}

@view_config(route_name='user', renderer='templates/user.jinja2')
def user(request):
    try:
        user = User.from_umid(request.matchdict['umid'])
        user_info_html = render('templates/user_info.jinja2',
            {'user': user, 'page': 'account'})

        return {'user': user,
                'user_info_block': user_info_html,
                'transactions': user.transactions}

    except InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='deposit', renderer='templates/deposit.jinja2')
def deposit(request):
    try:
        user = User.from_umid(request.matchdict['umid'])
        user_info_html = render('templates/user_info.jinja2', {'user': user,
                                                               'page': 'deposit'})
        keypad_html = render('templates/keypad.jinja2', {})
        return {'user_info_block': user_info_html, 'keypad': keypad_html}

    except InvalidUserException as e:
        request.session.flash('Invalid User ID.', 'error')
        return HTTPFound(location=request.route_url('index'))


@view_config(route_name='transaction')
def transaction_deposit(request):

    try:
        transaction = DBSession.query(Transaction) \
            .filter(Transaction.id==int(request.matchdict['transaction_id'])).one()

        # Choose which page to show based on the type of transaction
        if transaction.type == 'deposit':
            # View the deposit success page
            user = DBSession.query(User) \
                .filter(User.id==transaction.to_account_id).one()

            user_info_html = render('templates/user_info.jinja2',
                {'user': user, 'page': 'deposit'})
            
            deposit = {'transaction_id': transaction.id,
                       'prev': user.balance - transaction.amount,
                       'amount': transaction.amount,
                       'new': user.balance}
            return render_to_response('templates/deposit_complete.jinja2',
                {'deposit': deposit, 'user_info_block': user_info_html}, request)

        elif transaction.type == 'purchase':
            # View the purchase success page
            user = DBSession.query(User) \
                .filter(User.id==transaction.from_account_id).one()

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


###
### JSON Requests
###

@view_config(route_name='item', renderer='json')
def item(request):
    item = Item.from_barcode(request.matchdict['barcode'])
    item_html = render('templates/item_row.jinja2', {'item': item})
    return {'id':item.id, 'item_row_html' : item_html}

###
### POST Handlers
###

@view_config(route_name='purchase_new', request_method='POST', renderer='json')
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
        return {'transaction_id': purchase.id}

    except InvalidUserException as e:
        request.session.flash('Invalid user error. Please try again.', "error")
        return {'redirect_url': '/'}

    except ValueError as e:
        return {'error': 'Unable to parse Item ID or quantity'}

    except NoResultFound as e:
        # Could not find an item
        return {'error': 'Unable to identify an item.'}


@view_config(route_name='deposit_new', request_method='POST', renderer='json')
def deposit_new(request):
    try:
        user = User.from_umid(request.POST['umid'])
        amount = float(request.POST['amount'])

        if amount > 20.0:
            raise DepositException('Deposit amount of ${:,.2f} exceeds the limit'.format(amount))

        deposit = datalayer.deposit(user, amount)

        # Return a JSON blob of the transaction ID so the client can redirect to
        # the deposit success page
        return {'transaction_id': deposit['transaction'].id}

    except InvalidUserException as e:
        request.session.flash('Invalid user error. Please try again.', "error")
        return {'redirect_url': '/'}

    except ValueError as e:
        return {'error': 'Error understanding deposit amount.'}

    except DepositException as e:
        return {'error': str(e)}




###
### Admin
###

@view_config(route_name='admin_login', renderer='templates/admin/login.jinja2')
def admin_login(request):
    return {}

@view_config(route_name='admin_index', renderer='templates/admin/index.jinja2')
def admin_index(request):
    return {}

@view_config(route_name='admin_edit_items', renderer='templates/admin/edit_items.jinja2')
def admin_edit_items(request):
    items_active = DBSession.query(Item).filter_by(enabled=True).order_by(Item.name).all()
    items_inactive = DBSession.query(Item).filter_by(enabled=False).order_by(Item.name).all()
    items = items_active + items_inactive
    return {'items': items}

@view_config(route_name='admin_edit_items_submit', request_method='POST')
def admin_edit_items_submit(request):
    for key in request.POST:
        item = Item.from_id(int(key.split('-')[2]))
        setattr(item, key.split('-')[1], request.POST[key])
    request.session.flash("Items updated successfully.", "success")
    return HTTPFound(location=request.route_url('admin_edit_items'))

@view_config(route_name='admin_add_items', renderer='templates/admin/add_items.jinja2')
def admin_add_items(request):
    if len(request.GET) == 0:
        return {'items' : {'count': 1,
                'name-0': '',
                'barcode-0': '',
                'stock-0': '',
                'price-0': '',
                'wholesale-0': '',
                'enabled-0': '',
                }}
    else:
        d = {'items' : request.GET}
        return d

@view_config(route_name='admin_add_items_submit', request_method='POST')
def admin_add_items_submit(request):
    count = 0
    error_items = []
    for key in request.POST:
        if 'item-name-' in key:
            id = int(key.split('-')[2])
            try:
                name = request.POST['item-name-{}'.format(id)]
                barcode = request.POST['item-barcode-{}'.format(id)]
                stock = int(request.POST['item-stock-{}'.format(id)])
                price = float(request.POST['item-price-{}'.format(id)])
                wholesale = float(request.POST['item-wholesale-{}'.format(id)])
                try:
                    enabled = request.POST['item-enabled-{}'.format(id)] == 'on'
                except KeyError:
                    enabled = False
                item = Item(name, barcode, price, wholesale, stock, enabled)
                DBSession.add(item)
                count += 1
            except:
                if len(name):
                    try:
                        enabled = request.POST['item-enabled-{}'.format(id)] == 'on'
                    except KeyError:
                        enabled = False
                    error_items.append({
                            'name' : request.POST['item-name-{}'.format(id)],
                            'barcode' : request.POST['item-barcode-{}'.format(id)],
                            'stock' : request.POST['item-stock-{}'.format(id)],
                            'price' : request.POST['item-price-{}'.format(id)],
                            'wholesale' : request.POST['item-wholesale-{}'.format(id)],
                            'enabled' : enabled,
                            })
                    request.session.flash("Error adding item: {}".format(name), "error")
                # O/w this was probably a blank row; ignore.
    if count:
        request.session.flash("{} item{} added successfully.".format(count, ['s',''][count==1], "success"))
    else:
        request.session.flash("No items added.", "error")
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

@view_config(route_name='admin_inventory', renderer='templates/admin/inventory.jinja2')
def admin_inventory(request):
    items = DBSession.query(Item).all()
    return {'items': items}


@view_config(route_name='admin_edit_users', renderer='templates/admin/edit_users.jinja2')
def admin_edit_users(request):
    users = DBSession.query(User).all()
    for user in users:
        if user.disabled:
            user.enabled = False
        else:
            user.enabled = True
    roles = [('user', 'User'),
             ('serviceaccount', 'Service Account'),
             ('manager', 'Manager'),
             ('administrator', 'Administrator')]
    return {'users': users, 'roles': roles}

@view_config(route_name='admin_edit_users_submit', request_method='POST')
def admin_edit_users_submit(request):
    for key in request.POST:
        user = User.from_id(int(key.split('-')[2]))
        setattr(user, key.split('-')[1], request.POST[key])
    request.session.flash("Users updated successfully.", "success")
    return HTTPFound(location=request.route_url('admin_edit_users'))

