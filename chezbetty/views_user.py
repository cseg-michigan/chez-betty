from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.response import FileResponse
from pyramid.view import view_config, forbidden_view_config

from sqlalchemy.sql import func
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from . import views_data

from .models import *
from .models.model import *
from .models import user as __user
from .models.user import User
from .models.item import Item
from .models.box import Box
from .models.box_item import BoxItem
from .models.transaction import Transaction, Deposit, CashDeposit, BTCDeposit, Purchase
from .models.transaction import Inventory, InventoryLineItem
from .models.transaction import PurchaseLineItem, SubTransaction, SubSubTransaction
from .models.account import Account, VirtualAccount, CashAccount
from .models.event import Event
from .models import event as __event
from .models.vendor import Vendor
from .models.item_vendor import ItemVendor
from .models.box_vendor import BoxVendor
from .models.request import Request
from .models.announcement import Announcement
from .models.btcdeposit import BtcPendingDeposit
from .models.receipt import Receipt
from .models.pool import Pool
from .models.pool_user import PoolUser

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException

import stripe
import uuid
import math
import pytz
import traceback

###
### User Admin
###

@view_config(route_name='user_ajax_bool',
             permission='user')
def user_ajax_bool(request):
    obj_str = request.matchdict['object']
    obj_id  = int(request.matchdict['id'])
    obj_field = request.matchdict['field']
    obj_state = request.matchdict['state'].lower() == 'true'

    if obj_str == 'pool':
        obj = Pool.from_id(obj_id)
        if obj.owner != request.user.id:
            request.response.status = 502
            return request.response
    elif obj_str == 'pool_user':
        obj = PoolUser.from_id(obj_id)
        if obj.pool.owner != request.user.id:
            request.response.status = 502
            return request.response
    else:
        # Return an error, object type not recognized
        request.response.status = 502
        return request.response

    setattr(obj, obj_field, obj_state)
    DBSession.flush()

    return request.response

@view_config(route_name='user_index',
             renderer='templates/user/index.jinja2',
             permission='user')
def user_index(request):
    return {'user': request.user,
            'my_pools': Pool.all_by_owner(request.user)}

@view_config(route_name='user_deposit_cc',
             renderer='templates/user/deposit_cc.jinja2',
             permission='user')
def user_deposit_cc(request):
    return {'user': request.user,
            'stripe_pk': request.registry.settings['stripe.publishable_key'],
            }

@view_config(route_name='user_deposit_cc_submit',
             request_method='POST',
             permission='user')
def user_deposit_cc_submit(request):
    # See http://stripe.com/docs/tutorials/charges
    stripe.api_key = request.registry.settings['stripe.secret_key']

    token = request.POST['stripeToken']
    amount = float(request.POST['betty_amount'])
    total_cents = int(request.POST['betty_total_cents'])

    fee = amount * 0.029 + 0.30
    if total_cents != int(round((amount + fee)*100)):
        request.session.flash('Unexpected error processing transaction. Card NOT charged.', 'error')
        return HTTPFound(location=request.route_url('user_index'))
    amount = Decimal(amount)

    if amount <= 0.0:
        request.session.flash(
                _('Deposit amount must be greater than $0.00. Card NOT charged.'),
                'error'
                )
        return HTTPFound(location=request.route_url('user_index'))

    try:
        charge = stripe.Charge.create(
                amount = total_cents,
                currency="usd",
                source=token,
                description=request.user.uniqname+'@umich.edu'
                )

    except stripe.CardError as e:
        traceback.print_exc()
        request.session.flash('Card error processing transaction. Card NOT charged.', 'error')
        return HTTPFound(location=request.route_url('user_index'))
    except stripe.StripeError as e:
        traceback.print_exc()
        request.session.flash('Unexpected error processing transaction. Card NOT charged.', 'error')
        request.session.flash('Please e-mail chezbetty@umich.edu so we can correct this error', 'error')
        return HTTPFound(location=request.route_url('user_index'))

    try:
        # account = request.POST['account']
        account = 'user'

        if account == 'user':
            deposit = datalayer.deposit(request.user, request.user, amount)
        elif account == 'pool':
            deposit = datalayer.deposit(request.user, Pool.from_id(request.POST['pool_id']), amount)

        request.session.flash('Deposit added successfully.', 'success')

    except Exception as e:
        traceback.print_exc()
        request.session.flash('A unknown error has occured.', 'error')
        request.session.flash('Your card HAS been charged, but your account HAS NOT been credited.', 'error')
        request.session.flash('Please e-mail chezbetty@umich.edu so we can correct this error', 'error')

    return HTTPFound(location=request.route_url('user_index'))

@view_config(route_name='user_pools',
             renderer='templates/user/pools.jinja2',
             permission='user')
def user_pools(request):
    return {'user': request.user,
            'my_pools': Pool.all_by_owner(request.user)}


@view_config(route_name='user_pools_new_submit',
             request_method='POST',
             permission='user')
def user_pools_new_submit(request):
    try:
        pool_name = request.POST['pool-name'].strip()
        if len(pool_name) > 255:
            pool_name = pool_name[0:255]

        pool = Pool(request.user, pool_name)
        DBSession.add(pool)
        DBSession.flush()

        request.session.flash('Pool created.', 'succcess')
        return HTTPFound(location=request.route_url('user_pool', pool_id=pool.id))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error creating pool.', 'error')
        return HTTPFound(location=request.route_url('user_pools'))


@view_config(route_name='user_pool',
             renderer='templates/user/pool.jinja2',
             permission='user')
def user_pool(request):
    try:
        pool = Pool.from_id(request.matchdict['pool_id'])
        if pool.owner != request.user.id:
            request.session.flash('You do not have permission to view that pool.', 'error')
            return HTTPFound(location=request.route_url('user_pools'))

        return {'user': request.user,
                'pool': pool}
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Could not load pool.', 'error')
        return HTTPFound(location=request.route_url('user_pools'))


@view_config(route_name='user_pool_addmember_submit',
             request_method='POST',
             permission='user')
def user_pool_addmember_submit(request):
    try:
        pool = Pool.from_id(request.POST['pool-id'])
        if pool.owner != request.user.id:
            request.session.flash('You do not have permission to view that pool.', 'error')
            return HTTPFound(location=request.route_url('user_pools'))

        # Look up the user that is being added to the pool
        user = User.from_uniqname(request.POST['uniqname'].strip(), True)
        if user == None:
            request.session.flash('Could not find that user.', 'error')
            return HTTPFound(location=request.route_url('user_pool', pool_id=pool.id))

        # Can't add yourself
        if user.id == pool.owner:
            request.session.flash('You cannot add yourself to a pool. By owning the pool you are automatically a part of it.', 'error')
            return HTTPFound(location=request.route_url('user_pool', pool_id=pool.id))

        # Make sure the user isn't already in the pool
        for u in pool.users:
            if u.user_id == user.id:
                request.session.flash('User is already in pool.', 'error')
                return HTTPFound(location=request.route_url('user_pool', pool_id=pool.id))

        # Add the user to the pool
        pooluser = PoolUser(pool, user)
        DBSession.add(pooluser)
        DBSession.flush()

        request.session.flash('{} added to the pool.'.format(user.name), 'succcess')
        return HTTPFound(location=request.route_url('user_pool', pool_id=pool.id))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error adding user to pool.', 'error')
        return HTTPFound(location=request.route_url('user_pools'))




