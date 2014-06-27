from pyramid.renderers import render
from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from .models import *
from .models.model import *
from .models.user import User
from .models.item import Item

from .datalayer import *

@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    return {}

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
    item_html = render('templates/item_row.jinja2', {'item': item})
    return {'item_row_html' : item_row_html}

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

