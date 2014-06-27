from pyramid.renderers import render
from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from .models import *
import datalayer

@view_config(route_name='about', renderer='templates/about.jinja2')
def about(request):
    return {}

@view_config(route_name='purchase', renderer='templates/purchase.jinja2')
def purchase(request):
    return {}

@view_config(route_name='purchase_new', request_method='POST', renderer='templates/purchase_complete.jinja2')
def purchase_new(request):
    user = User.from_umid(request.matchdict['umid'])
    transaction = datalayer.purchase(user, request.POST.items())
    return {'transaction': transaction}

@view_config(route_name='items', renderer='templates/items.jinja2')
def items(request):
    items = DBSession.query(Item).all()
    return {'items': items}

@view_config(route_name='item', renderer='json')
def item(request):
    item = Item.from_barcode(request.matchdict['barcode'])
    item_html = render('templates/item.jinja2', {'item': item})
    return {'item_html' : item_html}

@view_config(route_name='users', renderer='templates/users.jinja2')
def users(request):
    users = DBSession.query(User).all()
    return {'users': users}

@view_config(route_name='user', renderer='templates/user.jinja2')
def user(request):
    user = User.from_umid(request.matchdict['umid'])
    return {'user': user}

@view_config(route_name='deposit', renderer='templates/deposit.jinja2')
def deposit(request):
    return {}

@view_config(route_name='deposit_new', request_method='POST', renderer='templates/deposit_new.jinja2')
def deposit_new(request):
    user = User.from_umid(request.POST['umid'])
    amount = float(request.POST['amount'])
    transaction = datalayer.deposit(user, amount)
    return {'transaction': transaction}


#######################
## Old testing / startup stubs

@view_config(route_name='home', renderer='templates/home.jinja2')
def my_view(request):
    return {'one': "fuck", 'project': 'chezbetty', 'name':'fuck'}

# /user/<swipe>/umid/uniqname>/json
@view_config(route_name="user_json", renderer="json")
def user_json(request):
    return {"id":1, "uniqname":"zakir", "umid":"95951361", "balance":10.00}

# /item/<barcode>/json
def lookup_item(route_name="item_json", renderer="json")
    return {"id":1, "price": 10.00, "name": "a goddamn granola bar", "in_stock": 10, "in_storage": 30}

