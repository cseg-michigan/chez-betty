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
import transaction

import traceback



@view_config(route_name='about', renderer='templates/public/about.jinja2')
def about(request):
    return {}


@view_config(route_name='items', renderer='templates/public/items.jinja2')
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


@view_config(route_name='item_request', renderer='templates/public/item_request.jinja2')
def item_request(request):
    return {}


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


@view_config(route_name='shame', renderer='templates/public/shame.jinja2')
def users(request):
    users = DBSession.query(User)\
                     .filter(User.balance < -5)\
                     .order_by(User.balance).all()
    return {'users': users}


@view_config(route_name='paydebt', renderer='templates/public/paydebt.jinja2')
def paydebt(request):
    uniqname = request.matchdict['uniqname']
    user = User.from_uniqname(uniqname, local_only=True)
    return {'user': user,
            'stripe_pk': request.registry.settings['stripe.publishable_key']}


@view_config(route_name='paydebt_submit',
             request_method='POST',
             renderer='json')
def paydebt_submit(request):
    uniqname = request.matchdict['uniqname']
    user = User.from_uniqname(uniqname, local_only=True)

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
            user)

    return {}
