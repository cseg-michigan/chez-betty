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
from .utility import post_stripe_payment

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException
import binascii
import transaction

import traceback

###
### Catch-all error page
###

@view_config(route_name='exception_view', renderer='templates/exception.jinja2')
def exception_view(request):
    return {}

@view_config(context=Exception)
def exception_view_handler(context, request):
    print('-'*80)
    print('An unknown error occurred:')
    print('\t** Some potentially useful information:')
    try:
        print('\t** request {}'.format(request))
        print('\t** client_addr {}'.format(request.client_addr))
        print('\t** authenticated_userid {}'.format(request.authenticated_userid))
        print('\t** GET {}'.format(request.GET))
        print('\t** POST {}'.format(request.POST))
        print('\t** url {}'.format(request.url))
        print('\t** user_agent {}'.format(request.user_agent))
        print('\t** headers.environ {}'.format(request.headers.environ))
        print('\t** referer {}'.format(request.referer))
        print('\t** body {}'.format(request.body))
    except:
        pass
    traceback.print_exc()
    print('-'*80)
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




from pyramid.view import view_config

# Use to select which homepage to show, the only-on-the-betty-terminal version
# or the publically accessible version.   
def IsTerminalPredicate(boolean):
    def is_terminal(context, request):
        return ((request.user != None) and (request.user.role == 'serviceaccount')) == boolean
    return is_terminal



# Terminal home page
@view_config(route_name='index',
             renderer='templates/terminal/index.jinja2',
             custom_predicates=(IsTerminalPredicate(True),))
def index_terminal(request):
    announcements = Announcement.all_enabled()

    try:
        top_debtors = DBSession.query(User)\
                         .filter(User.balance < -5)\
                         .order_by(User.balance)\
                         .limit(5).all()
    except NoResultFound:
        top_debtors = None

    # For the demo mode
    if 'demo' in request.cookies and request.cookies['demo'] == '1':
        admins = User.get_admins()
    else:
        admins = []

    shame_users = User.get_shame_users()

    return {
            'announcements': announcements,
            'admins': admins,
            'top_debtors': top_debtors,
            'owed_by_users': User.get_amount_owed(),
            'shame_users': shame_users,
            }


# General internet homepage
@view_config(route_name='index',
             renderer='templates/index.jinja2',
             custom_predicates=(IsTerminalPredicate(False),))
def index(request):
    announcements = Announcement.all_enabled()
    for announcement in announcements:
        request.session.flash(announcement.announcement, 'info')

    try:
        top_debtors = DBSession.query(User)\
                         .filter(User.balance < -5)\
                         .order_by(User.balance)\
                         .limit(5).all()
    except NoResultFound:
        top_debtors = None

    shame_users = DBSession.query(User)\
                     .filter(User.balance < -5)\
                     .order_by(User.balance).all()

    return {
            'top_debtors': top_debtors,
            'owed_by_users': User.get_amount_owed(),
            'shame_users': shame_users,
            }


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


@view_config(route_name='paydebt', renderer='templates/paydebt.jinja2')
def paydebt(request):
    uniqname = request.matchdict['uniqname']
    user = User.from_uniqname(uniqname, local_only=True)
    return {
            'user': user,
            'stripe_pk': request.registry.settings['stripe.publishable_key'],
            }

@view_config(route_name='paydebt_submit',
             request_method='POST',
             renderer='json',
             )
def paydebt_submit(request):
    uniqname = request.matchdict['uniqname']
    user = User.from_uniqname(uniqname, local_only=True)

    print(request.POST)

    token = request.POST['stripeToken']
    amount = float(request.POST['betty_amount'])
    total_cents = int(request.POST['betty_total_cents'])

    post_stripe_payment(
            datalayer,
            request,
            token,
            amount,
            total_cents,
            user,
            user,
            )

    return {}

