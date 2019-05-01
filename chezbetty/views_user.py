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
from .models.transaction import Transaction, Deposit, CashDeposit, CCDeposit, BTCDeposit, Purchase
from .models.transaction import Inventory, InventoryLineItem
from .models.transaction import PurchaseLineItem, SubTransaction, SubSubTransaction
from .models.account import Account, VirtualAccount, CashAccount
from .models.event import Event
from .models import event as __event
from .models.vendor import Vendor
from .models.item_vendor import ItemVendor
from .models.box_vendor import BoxVendor
from .models.request import Request
from .models.request_post import RequestPost
from .models.announcement import Announcement
from .models.btcdeposit import BtcPendingDeposit
from .models.receipt import Receipt
from .models.pool import Pool
from .models.pool_user import PoolUser

from .utility import post_stripe_payment

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException

import uuid
import math
import pytz
import traceback
import arrow

###
### User Admin
###


### Common helper code

def transaction_history_queries(request, user_or_pool):
    # Web library native date format: 2015/06/19 19:00
    # DO NOT CHANGE: The datetimepicker has a bug and tries to parse the
    #                prepopulated value before reading the format string,
    #                which means you have to use its native format string
    TS_FORMAT = 'YYYY/MM/DD HH:mm'
    if 'history-end' not in request.GET:
        request.GET['history-end'] =\
                arrow.now()\
                .replace(hours=+1)\
                .floor('hour')\
                .format(TS_FORMAT)
    if 'history-start' not in request.GET:
        request.GET['history-start'] =\
                arrow.get(request.GET['history-end'], TS_FORMAT)\
                .replace(months=-1)\
                .format(TS_FORMAT)

    start = arrow.get(request.GET['history-start'], TS_FORMAT)
    end   = arrow.get(request.GET['history-end'],   TS_FORMAT)
    start = start.replace(tzinfo='US/Eastern')
    end   = end  .replace(tzinfo='US/Eastern')
    start = start.to('utc')
    end   = end  .to('utc')

    query = user_or_pool.get_transactions_query()
    query = query\
            .filter(event.Event.timestamp > start.datetime)\
            .filter(event.Event.timestamp < end.datetime)

    for t in ('purchase', 'adjustment'):
        if 'history-filter-'+t in request.GET:
            query = query.filter(event.Event.type!=t)
    for t in ('cashdeposit', 'ccdeposit', 'btcdeposit'):
        if 'history-filter-'+t in request.GET:
            query = query.filter(Transaction.type!=t)
    transactions = query.all()

    withdrawls  = query.filter(event.Event.type=='purchase').all()
    deposits    = query.filter(event.Event.type=='deposit').all()
    adjustments = query.filter(event.Event.type=='adjustment').all()

    withdrawls  = sum(w.amount for w in withdrawls)
    deposits    = sum(d.amount for d in deposits)
    adjustments = sum(a.amount for a in adjustments) if len(adjustments) else None

    return {'transactions': transactions,
            'withdrawls': withdrawls,
            'deposits': deposits,
            'adjustments': adjustments,
            }



@view_config(route_name='user_ajax_bool',
             permission='user')
def user_ajax_bool(request):
    obj_str = request.matchdict['object']
    obj_id  = int(request.matchdict['id'])
    obj_field = request.matchdict['field']
    obj_state = request.matchdict['state'].lower() == 'true'

    if obj_str == 'pool':
        obj = Pool.from_id(obj_id)
        obj_owner_id = obj.owner
    elif obj_str == 'pool_user':
        obj = PoolUser.from_id(obj_id)
        obj_owner_id = obj.pool.owner
    elif obj_str == 'request_post':
        obj = RequestPost.from_id(obj_id)
        obj_owner_id = obj.user_id
    else:
        # Return an error, object type not recognized
        request.response.status = 502
        return request.response

    if obj_owner_id != request.user.id:
        request.response.status = 502
        return request.response

    setattr(obj, obj_field, obj_state)
    DBSession.flush()

    return request.response

@view_config(route_name='user_index',
             renderer='templates/user/index.jinja2',
             permission='user')
def user_index(request):
    r = transaction_history_queries(request, request.user)
    r['user'] = request.user
    r['my_pools'] = Pool.all_by_owner(request.user)

    return r

@view_config(route_name='user_index_slash',
             renderer='templates/user/index.jinja2',
             permission='user')
def user_index_slash(request):
    return HTTPFound(location=request.route_url('user_index'))

@view_config(route_name='user_deposit_cc',
             renderer='templates/user/deposit_cc.jinja2',
             permission='user')
def user_deposit_cc(request):
    pools = Pool.all_accessable(request.user, True)
    pool = None
    if 'acct' in request.GET:
        account = request.GET['acct']
        if account != 'user':
            pool = Pool.from_id(account.split('-')[1])
    else:
        account = 'user'
    return {'user': request.user,
            'account': account,
            'pool': pool,
            'pools': pools,
            'stripe_pk': request.registry.settings['stripe.publishable_key'],
            }

@view_config(route_name='user_deposit_cc_custom',
             renderer='templates/user/deposit_cc_custom.jinja2',
             permission='user')
def user_deposit_cc_custom(request):
    try:
        # Check that the custom deposit amount is valid.
        amount = round(Decimal(request.GET['deposit-amount']), 2)

        account = request.GET['betty_to_account']
        if account != 'user':
            pool = Pool.from_id(account.split('-')[1])
        else:
            pool = None
        return {'user': request.user,
                'stripe_pk': request.registry.settings['stripe.publishable_key'],
                'amount': round(Decimal(request.GET['deposit-amount']), 2),
                'account': account,
                'pool': pool,
                }
    except Exception as e:
        request.session.flash('Please enter a valid custom deposit amount.', 'error')
        return HTTPFound(location=request.route_url('user_deposit_cc'))


@view_config(route_name='user_deposit_cc_submit',
             request_method='POST',
             permission='user')
def user_deposit_cc_submit(request):
    token = request.POST['stripeToken']
    amount = Decimal(request.POST['betty_amount'])
    total_cents = int(request.POST['betty_total_cents'])
    to_account = request.POST['betty_to_account']

    try:
        if to_account != 'user':
            pool = Pool.from_id(to_account.split('-')[1])
            if pool.enabled == False:
                print("to_account:", to_account)
                raise NotImplementedError
            if pool.owner != request.user.id:
                if pool not in map(lambda pu: getattr(pu, 'pool'), request.user.pools):
                    print("to_account:", to_account)
                    raise NotImplementedError
    except Exception as e:
        traceback.print_exc()
        request.session.flash('Unexpected error processing transaction. Card NOT charged.', 'error')
        return HTTPFound(location=request.route_url('user_index'))

    post_stripe_payment(
            datalayer,
            request,
            token,
            amount,
            total_cents,
            request.user,
            request.user if to_account == 'user' else pool,
            )

    return HTTPFound(location=request.route_url('user_index'))



@view_config(route_name='user_item_list',
             renderer='templates/user/item_list.jinja2',
             permission='user')
def item_list(request):
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


@view_config(route_name='user_ajax_item_request_fuzzy',
             renderer='templates/user/item_request_fuzzy.jinja2',
             permission='user')
def item_request_fuzzy(request):
    new_item = request.POST['new_item']
    matches = DBSession.query(Item)\
            .filter(Item.name.ilike('%'+new_item+'%'))\
            .order_by(Item.name)
    enabled = matches.filter(Item.enabled==True)
    in_stock = enabled.filter(Item.in_stock>0).all()
    out_of_stock = enabled.filter(Item.in_stock==0).all()
    for item in out_of_stock:
        purchase = SubTransaction.all_item_purchases(item.id, limit=1)[0]
        item.most_recent_purchase = purchase
    disabled = matches.filter(Item.enabled==False).all()
    return {
            'in_stock': in_stock,
            'out_of_stock': out_of_stock,
            'disabled': disabled,
            }


@view_config(route_name='user_item_request',
             renderer='templates/user/item_request.jinja2',
             permission='user')
def item_request(request):
    requests = Request.all()
    vendors = Vendor.all()
    return {
            'requests': requests,
            'vendors': vendors,
           }


@view_config(route_name='user_item_request_new',
             request_method='POST',
             permission='user')
def item_request_new(request):
    try:
        request_text = request.POST['request']
        vendor_id = request.POST['vendor']
        vendor = Vendor.from_id(vendor_id)
        vendor_url = request.POST['vendor-url']
        if len(request_text) < 5:
            raise ValueError()

        datalayer.new_request(request.user, request_text, vendor, vendor_url)

        request.session.flash('Request added successfully', 'success')
        return HTTPFound(location=request.route_url('user_item_request'))

    except ValueError:
        request.session.flash('Please include a detailed description of the item.', 'error')
        return HTTPFound(location=request.route_url('user_item_request'))

    except:
        request.session.flash('Error adding request.', 'error')
        return HTTPFound(location=request.route_url('user_item_request'))


@view_config(route_name='user_item_request_post_new',
             request_method='POST',
             permission='user')
def item_request_post_new(request):
    try:
        item_request = Request.from_id(request.matchdict['id'])
        post_text = request.POST['post']
        if post_text.strip() == '':
            request.session.flash('Empty comment not saved.', 'error')
            return HTTPFound(location=request.route_url('user_item_request'))
        post = RequestPost(item_request, request.user, post_text)
        DBSession.add(post)
        DBSession.flush()
    except Exception as e:
        if request.debug:
            raise(e)
        else:
            print(e)
        request.session.flash('Error posting comment.', 'error')
    return HTTPFound(location=request.route_url('user_item_request'))




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
        if len(pool_name) < 5:
            request.session.flash('Pool names must be at least 5 letters long', 'error')
            return HTTPFound(location=request.route_url('user_pools'))

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

        r = transaction_history_queries(request, pool)
        r['user'] = request.user
        r['pool'] = pool

        return r
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


@view_config(route_name='user_pool_changename_submit',
             request_method='POST',
             permission='user')
def user_pool_changename_submit(request):
    try:
        pool = Pool.from_id(request.POST['pool-id'])
        if pool.owner != request.user.id:
            request.session.flash('You do not have permission to view that pool.', 'error')
            return HTTPFound(location=request.route_url('user_pools'))

        pool_name = request.POST['newname'].strip()
        if len(pool_name) > 255:
            pool_name = pool_name[0:255]
        if len(pool_name) < 5:
            request.session.flash('Pool names must be at least 5 letters long', 'error')
            return HTTPFound(location=request.route_url('user_pool', pool_id=int(pool.id)))

        pool.name = pool_name

        request.session.flash('Pool created.', 'succcess')
        return HTTPFound(location=request.route_url('user_pool', pool_id=pool.id))
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error changing pool name.', 'error')
        return HTTPFound(location=request.route_url('user_pools'))


@view_config(route_name='user_password_edit',
             renderer='templates/user/password_edit.jinja2',
             permission='user')
def user_password_edit(request):
    return {}


@view_config(route_name='user_password_edit_submit',
             request_method='POST',
             permission='user')
def user_password_edit_submit(request):
    pwd0 = request.POST['edit-password-0']
    pwd1 = request.POST['edit-password-1']
    if pwd0 != pwd1:
        request.session.flash('Error: Passwords do not match', 'error')
        return HTTPFound(location=request.route_url('user_password_edit'))
    request.user.password = pwd0
    request.session.flash('Password changed successfully.', 'success')
    return HTTPFound(location=request.route_url('user_index'))
    # check that changing password for actually logged in user


