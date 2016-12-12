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
from .models.user import User, InvalidUserException
from .models.item import Item, ItemImage
from .models.box import Box
from .models.box_item import BoxItem
from .models.transaction import Transaction, Deposit, CashDeposit, BTCDeposit, CCDeposit, Purchase
from .models.transaction import Inventory, InventoryLineItem, RestockLineItem, RestockLineBox
from .models.transaction import PurchaseLineItem, SubTransaction, SubSubTransaction
from .models.account import Account, VirtualAccount, CashAccount, get_virt_account, get_cash_account
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
from .models.tag import Tag
from .models.item_tag import ItemTag
from .models.reimbursee import Reimbursee
from .models.badscan import BadScan

from .utility import suppress_emails
from .utility import send_email
from .utility import send_bcc_email
from .utility import user_password_reset

from .jinja2_filters import format_currency

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException
import transaction

# Used for generating barcodes
from reportlab.graphics.barcode import code39
from reportlab.graphics.barcode import code93
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas

import abbreviate
import arrow
import uuid
import twitter
import traceback
import math
import pytz
import io
from PIL import Image



###
### Global Attributes (passed to every template)
###   - n.b. This really is global, it will pick up views routes too
###
# Add counts to all rendered pages for the sidebar
# Obviously don't need this for json requests
@subscriber(BeforeRender)
def add_counts(event):
    if event['renderer_name'] != 'json' and \
       event['renderer_name'].startswith('templates/admin'):
        count = {}
        count['items']        = Item.count()
        count['tags']         = Tag.count()
        count['boxes']        = Box.count()
        count['vendors']      = Vendor.count()
        count['users']        = User.count()
        count['transactions'] = Transaction.count()
        count['restocks']     = Transaction.count(trans_type="restock")
        count['requests']     = Request.count()
        count['pools']        = Pool.count()
        count['reimbursees']  = Reimbursee.count()
        event.rendering_val['counts'] = count

@subscriber(BeforeRender)
def is_terminal(event):
    try:
        if event['request'].remote_addr == event['request'].registry.settings['chezbetty.ipaddr']:
            event['request'].is_terminal = True
        else:
            event['request'].is_terminal = False
    except Exception as e:
        if 'request' in event and event['request']:
            event['request'].is_terminal = False

###
### Admin
###

def _admin_ajax_general(request, obj_value):
    obj_str = request.matchdict['object']
    obj_id  = int(request.matchdict['id'])
    obj_field = request.matchdict['field']

    if obj_str == 'item':
        obj = Item.from_id(obj_id)
    elif obj_str == 'announcement':
        obj = Announcement.from_id(obj_id)
    elif obj_str == 'box':
        obj = Box.from_id(obj_id)
    elif obj_str == 'vendor':
        obj = Vendor.from_id(obj_id)
    elif obj_str == 'user':
        obj = User.from_id(obj_id)
    elif obj_str == 'request':
        obj = Request.from_id(obj_id)
    elif obj_str == 'request_post':
        obj = RequestPost.from_id(obj_id)
    elif obj_str == 'pool':
        obj = Pool.from_id(obj_id)
    elif obj_str == 'pool_user':
        obj = PoolUser.from_id(obj_id)
    elif obj_str == 'tag':
        obj = Tag.from_id(obj_id)
    elif obj_str == 'itemtag':
        obj = ItemTag.from_id(obj_id)
    elif obj_str == 'cookie':
        # Set a cookie instead of change a property
        if type(obj_value) == bool:
            request.response.set_cookie(obj_field, '1' if obj_value else '0')
        else:
            request.response.set_cookie(obj_field, str(obj_value))
        return request.response
    else:
        # Return an error, object type not recognized
        raise TypeError


    setattr(obj, obj_field, obj_value)

    DBSession.flush()


@view_config(route_name='admin_ajax_bool', permission='admin')
def admin_ajax_bool(request):
    obj_value = request.matchdict['value'].lower() == 'true'
    try:
        _admin_ajax_general(request, obj_value)
    except Exception as e:
        if request.debug:
            raise(e)
        request.response.status = 400
    return request.response

@view_config(route_name='admin_ajax_text',
             renderer='json',
             permission='admin')
def admin_ajax_text(request):
    obj_value = request.POST['value']
    _admin_ajax_general(request, obj_value)
    return {
            'status': 'success',
            'msg': 'Saved.',
            'value': obj_value,
           }


@view_config(route_name='admin_ajax_new',
             renderer='json',
             permission='admin')
def admin_ajax_new(request):
    obj_str = request.matchdict['object']
    obj_arg = request.matchdict['arg']

    if obj_str == 'tag':
        mod = Tag
    else:
        # Return an error, object type not recognized
        request.response.status = 502
        return request.response

    new_thing = mod(obj_arg)
    DBSession.add(new_thing)
    DBSession.flush()

    return {'id': new_thing.id,
            'arg': obj_arg}


@view_config(route_name='admin_ajax_delete',
             renderer='json',
             permission='admin')
def admin_ajax_delete(request):
    obj_str = request.matchdict['object']
    obj_id  = request.matchdict['id']

    if obj_str == 'badscan':
        BadScan.delete_scans(obj_id)
    else:
        # Return an error, object type not recognized
        request.response.status = 502
        return request.response

    return {'status': 'success'}


@view_config(route_name='admin_ajax_connection',
             renderer='json',
             permission='admin')
def admin_ajax_connection(request):
    obj_str1 = request.matchdict['object1']
    obj_str2 = request.matchdict['object2']
    obj_arg1 = request.matchdict['arg1']
    obj_arg2 = request.matchdict['arg2']

    out = {'arg1': obj_arg1,
           'arg2': obj_arg2}

    if obj_str1 == 'item':
        item = Item.from_id(int(obj_arg1))

        if obj_str2 == 'tag':
            tag = Tag.from_id(int(obj_arg2))

            # Make sure we don't already have this tag
            for t in item.tags:
                if t.tag.id == tag.id:
                    break
            else:
                itemtag = ItemTag(item, tag)
                DBSession.add(itemtag)
                DBSession.flush()

                out['tag_name'] = tag.name
                out['item_tag_id'] = itemtag.id

    else:
        # Return an error, object type not recognized
        request.response.status = 502
        return request.response

    DBSession.flush()

    return out


@view_config(route_name='admin_ajaxed_field',
             renderer='json',
             permission='manage')
def admin_ajaxed_field(request):
    field = request.matchdict['field']
    if field == 'index-bitcoin':
        try:
            btc_balance = Bitcoin.get_balance()
            btc = {"btc": btc_balance,
                   "mbtc": round(btc_balance*1000, 2),
                   "usd": btc_balance * Bitcoin.get_spot_price()}
            html='{} mBTC ({})'.format(btc['mbtc'], format_currency(btc['usd']))
            return dict(html=html)
        except BTCException:
            return dict(html='Error loading BTC Value')
    request.session.flash('No handler for ajaxed field: {}'.format(field), 'error')


@view_config(route_name='admin_index',
             renderer='templates/admin/index.jinja2',
             permission='manage')
def admin_index(request):
    events          = Event.some(10)
    users_shame     = DBSession.query(User)\
                               .filter(User.balance < 0)\
                               .order_by(User.balance)\
                               .limit(5).all()
    users_balance   = User.get_users_total()
    held_for_users  = User.get_amount_held()
    owed_by_users   = User.get_amount_owed()

    inventory       = DBSession.query(func.sum(Item.in_stock * Item.wholesale).label("wholesale"),
                                      func.sum(Item.in_stock * Item.price).label("price")).one()

    owed_reimbursements = Reimbursee.get_owed()

    debt_forgiven   = User.get_debt_forgiven()
    balance_absorbed= User.get_amount_absorbed()

    chezbetty       = get_virt_account("chezbetty")
    safe            = get_cash_account("safe")
    cashbox         = get_cash_account("cashbox")
    btcbox          = get_cash_account("btcbox")
    chezbetty_cash  = get_cash_account("chezbetty")

    cashbox_lost    = Transaction.get_balance("lost", account.get_cash_account("cashbox"))
    safe_lost       = Transaction.get_balance("lost", account.get_cash_account("safe"))
    cashbox_found   = Transaction.get_balance("found", account.get_cash_account("cashbox"))
    safe_found      = Transaction.get_balance("found", account.get_cash_account("safe"))
    btcbox_lost     = Transaction.get_balance("lost", account.get_cash_account("btcbox"))
    btcbox_found    = Transaction.get_balance("found", account.get_cash_account("btcbox"))
    chezbetty_lost  = Transaction.get_balance("lost", account.get_cash_account("chezbetty"))
    chezbetty_found = Transaction.get_balance("found", account.get_cash_account("chezbetty"))
    restock         = Transaction.get_balance("restock", account.get_cash_account("chezbetty"))
    donation        = Transaction.get_balance("donation", account.get_cash_account("chezbetty"))
    withdrawal      = Transaction.get_balance("withdrawal", account.get_cash_account("chezbetty"))

    cashbox_net = (cashbox_found.balance - cashbox_lost.balance) + (safe_found.balance - safe_lost.balance)
    btcbox_net = btcbox_found.balance - btcbox_lost.balance
    chezbetty_net = chezbetty_found.balance - chezbetty_lost.balance
    # Our "shut it down" balance. Basically what we would have left over if
    # refunded all account holders, defaulted on our loan, and sold all inventory
    # for what we paid for it.
    estimated_net = chezbetty_cash.balance + safe.balance + cashbox.balance + btcbox.balance - held_for_users + inventory.wholesale

    # Get the current date that it is in the eastern time zone
    now = arrow.now()

    # Walk back to the beginning of the day for all these statistics
    now = now.replace(hour=0, minute=0, second=0)

    today_sales     = Purchase.total(start=now)
    today_profit    = PurchaseLineItem.profit_on_sales(start=now)
    today_lost      = Inventory.total(start=now)
    today_dep       = Deposit.total(start=now)
    today_dep_cash  = CashDeposit.total(start=now)
    today_dep_btc   = BTCDeposit.total(start=now)
    today_dep_cc    = CCDeposit.total(start=now)
    today_discounts = Purchase.discounts(start=now)
    today_fees      = Purchase.fees(start=now)
    today_users     = Purchase.distinct(distinct_on=Event.user_id, start=now)
    today_new_users = User.get_number_new_users(start=now)

    # Also get statistics for yesterday
    yesterday = now - datetime.timedelta(days=1)

    yesterday_sales     = Purchase.total(start=yesterday, end=now)
    yesterday_profit    = PurchaseLineItem.profit_on_sales(start=yesterday, end=now)
    yesterday_lost      = Inventory.total(start=yesterday, end=now)
    yesterday_dep       = Deposit.total(start=yesterday, end=now)
    yesterday_dep_cash  = CashDeposit.total(start=yesterday, end=now)
    yesterday_dep_btc   = BTCDeposit.total(start=yesterday, end=now)
    yesterday_dep_cc    = CCDeposit.total(start=yesterday, end=now)
    yesterday_discounts = Purchase.discounts(start=yesterday, end=now)
    yesterday_fees      = Purchase.fees(start=yesterday, end=now)
    yesterday_users     = Purchase.distinct(distinct_on=Event.user_id, start=yesterday, end=now)
    yesterday_new_users = User.get_number_new_users(start=yesterday, end=now)

    return dict(events=events,
                users_shame=users_shame,
                users_balance=users_balance,
                held_for_users=held_for_users,
                owed_by_users=owed_by_users,
                owed_reimbursements=owed_reimbursements,
                debt_forgiven=debt_forgiven,
                balance_absorbed=balance_absorbed,
                safe=safe,
                cashbox=cashbox,
                btcbox=btcbox,
                chezbetty_cash=chezbetty_cash,
                chezbetty=chezbetty,
                cashbox_net=cashbox_net,
                btcbox_net=btcbox_net,
                chezbetty_net=chezbetty_net,
                estimated_net=estimated_net,
                restock=restock,
                donation=donation,
                withdrawal=withdrawal,
                inventory=inventory,
                today_sales=today_sales,
                today_profit=today_profit,
                today_lost=today_lost,
                today_dep=today_dep,
                today_dep_cash=today_dep_cash,
                today_dep_btc=today_dep_btc,
                today_dep_cc=today_dep_cc,
                today_discounts=today_discounts,
                today_fees=today_fees,
                today_users=today_users,
                today_new_users=today_new_users,
                yesterday_sales=yesterday_sales,
                yesterday_profit=yesterday_profit,
                yesterday_lost=yesterday_lost,
                yesterday_dep=yesterday_dep,
                yesterday_dep_cash=yesterday_dep_cash,
                yesterday_dep_btc=yesterday_dep_btc,
                yesterday_dep_cc=yesterday_dep_cc,
                yesterday_discounts=yesterday_discounts,
                yesterday_fees=yesterday_fees,
                yesterday_users=yesterday_users,
                yesterday_new_users=yesterday_new_users,
                )


@view_config(route_name='admin_index_dashboard',
             renderer='templates/admin/dashboard.jinja2',
             permission='manage')
def admin_dashboard(request):

    bsi             = DBSession.query(func.sum(PurchaseLineItem.quantity).label('quantity'), Item)\
                               .join(Item)\
                               .join(Transaction)\
                               .join(Event)\
                               .filter(Transaction.type=='purchase')\
                               .filter(Event.deleted==False)\
                               .group_by(Item.id)\
                               .order_by(desc('quantity'))\
                               .limit(5).all()

    total_sales          = Purchase.total()
    profit_on_sales      = PurchaseLineItem.profit_on_sales()
    total_inventory_lost = Inventory.total()
    total_deposits       = Deposit.total()
    total_cash_deposits  = CashDeposit.total()
    total_btc_deposits   = BTCDeposit.total()
    total_cc_deposits    = CCDeposit.total()
    total_active_users   = Purchase.distinct(distinct_on=Event.user_id)

    cashbox_lost    = Transaction.get_balance("lost", account.get_cash_account("cashbox"))
    cashbox_found   = Transaction.get_balance("found", account.get_cash_account("cashbox"))
    btcbox_lost     = Transaction.get_balance("lost", account.get_cash_account("btcbox"))
    btcbox_found    = Transaction.get_balance("found", account.get_cash_account("btcbox"))
    chezbetty_lost  = Transaction.get_balance("lost", account.get_cash_account("chezbetty"))
    chezbetty_found = Transaction.get_balance("found", account.get_cash_account("chezbetty"))
    restock         = Transaction.get_balance("restock", account.get_cash_account("chezbetty"))
    donation        = Transaction.get_balance("donation", account.get_cash_account("chezbetty"))
    withdrawal      = Transaction.get_balance("withdrawal", account.get_cash_account("chezbetty"))

    cashbox_net   = cashbox_found.balance - cashbox_lost.balance
    btcbox_net    = btcbox_found.balance - btcbox_lost.balance
    chezbetty_net = chezbetty_found.balance - chezbetty_lost.balance

    # Get the current date that it is in the eastern time zone
    now = arrow.now()

    # Walk back to the beginning of the day for all these statistics
    now = now.replace(hour=0, minute=0, seconds=0)

    ytd_sales     = Purchase.total(start=now.replace(month=1,day=1), end=None)
    ytd_profit    = PurchaseLineItem.profit_on_sales(start=now.replace(month=1,day=1), end=None)
    ytd_lost      = Inventory.total(start=now.replace(month=1,day=1), end=None)
    ytd_dep       = Deposit.total(start=now.replace(month=1,day=1), end=None)
    ytd_dep_cash  = CashDeposit.total(start=now.replace(month=1,day=1), end=None)
    ytd_dep_btc   = BTCDeposit.total(start=now.replace(month=1,day=1), end=None)
    ytd_dep_cc    = CCDeposit.total(start=now.replace(month=1,day=1), end=None)
    ytd_discounts = Purchase.discounts(start=now.replace(month=1,day=1), end=None)
    ytd_fees      = Purchase.fees(start=now.replace(month=1,day=1), end=None)
    ytd_users     = Purchase.distinct(distinct_on=Event.user_id, start=now.replace(month=1, day=1))
    ytd_new_users = User.get_number_new_users(start=now.replace(month=1, day=1))

    mtd_sales     = Purchase.total(start=now.replace(day=1), end=None)
    mtd_profit    = PurchaseLineItem.profit_on_sales(start=now.replace(day=1), end=None)
    mtd_lost      = Inventory.total(start=now.replace(day=1), end=None)
    mtd_dep       = Deposit.total(start=now.replace(day=1), end=None)
    mtd_dep_cash  = CashDeposit.total(start=now.replace(day=1), end=None)
    mtd_dep_btc   = BTCDeposit.total(start=now.replace(day=1), end=None)
    mtd_dep_cc    = CCDeposit.total(start=now.replace(day=1), end=None)
    mtd_discounts = Purchase.discounts(start=now.replace(day=1), end=None)
    mtd_fees      = Purchase.fees(start=now.replace(day=1), end=None)
    mtd_users     = Purchase.distinct(distinct_on=Event.user_id, start=now.replace(day=1))
    mtd_new_users = User.get_number_new_users(start=now.replace(day=1))

    graph_deposits_day_total = views_data.create_dict('deposits', 'day', 21)
    graph_deposits_day_cash  = views_data.create_dict('deposits_cash', 'day', 21)
    graph_deposits_day_btc   = views_data.create_dict('deposits_btc', 'day', 21)
    graph_deposits_day = {'xs': [graph_deposits_day_total['xs'][0],
                                 graph_deposits_day_cash['xs'][0],
                                 graph_deposits_day_btc['xs'][0]],
                          'ys': [graph_deposits_day_total['ys'][0],
                                 graph_deposits_day_cash['ys'][0],
                                 graph_deposits_day_btc['ys'][0]],
                          'avg_hack': [graph_deposits_day_total['avg_hack'][0],
                                 graph_deposits_day_cash['avg_hack'][0],
                                 graph_deposits_day_btc['avg_hack'][0]]}


    def metrics_per_time(start, end):
        print(Transaction.get_balance("restock", account.get_cash_account("chezbetty"), start=start, end=end))

        return {
            "sales":      Purchase.total(start=start, end=end),
            "profit":     PurchaseLineItem.profit_on_sales(start=start, end=end),
            "lost":       Inventory.total(start=start, end=end),
            "dep":        Deposit.total(start=start, end=end),
            "dep_cash":   CashDeposit.total(start=start, end=end),
            "dep_btc":    BTCDeposit.total(start=start, end=end),
            "dep_cc":     CCDeposit.total(start=start, end=end),
            "discounts":  Purchase.discounts(start=start, end=end),
            "fees":       Purchase.fees(start=start, end=end),
            "users":      Purchase.distinct(distinct_on=Event.user_id, start=start, end=end),
            "new_users":  User.get_number_new_users(start=start, end=end),
            "cashbox_lost": Transaction.get_balance("lost", account.get_cash_account("cashbox"), start=start, end=end).balance,
            # safe_lost       = Transaction.get_balance("lost", account.get_cash_account("safe"))
            # cashbox_found   = Transaction.get_balance("found", account.get_cash_account("cashbox"))
            # safe_found      = Transaction.get_balance("found", account.get_cash_account("safe"))
            # btcbox_lost     = Transaction.get_balance("lost", account.get_cash_account("btcbox"))
            # btcbox_found    = Transaction.get_balance("found", account.get_cash_account("btcbox"))
            # chezbetty_lost  = Transaction.get_balance("lost", account.get_cash_account("chezbetty"))
            # chezbetty_found = Transaction.get_balance("found", account.get_cash_account("chezbetty"))
            "store":          Transaction.get_balance("restock", account.get_cash_account("chezbetty"), start=start, end=end).balance,
            # donation        = Transaction.get_balance("donation", account.get_cash_account("chezbetty"))
            # withdrawal      = Transaction.get_balance("withdrawal", account.get_cash_account("chezbetty"))
        }


    metrics_2014 = metrics_per_time(arrow.get(2014, 1, 1), arrow.get(2015, 1, 1))


    return dict(best_selling_items=bsi,
                total_sales=total_sales,
                profit_on_sales=profit_on_sales,
                total_inventory_lost=total_inventory_lost,
                total_deposits=total_deposits,
                total_cash_deposits=total_cash_deposits,
                total_btc_deposits=total_btc_deposits,
                total_cc_deposits=total_cc_deposits,
                total_active_users=total_active_users,
                restock=restock,
                cashbox_net=cashbox_net,
                btcbox_net=btcbox_net,
                chezbetty_net=chezbetty_net,
                ytd_sales=ytd_sales,
                ytd_profit=ytd_profit,
                ytd_lost=ytd_lost,
                ytd_dep=ytd_dep,
                ytd_dep_cash=ytd_dep_cash,
                ytd_dep_btc=ytd_dep_btc,
                ytd_dep_cc=ytd_dep_cc,
                ytd_discounts=ytd_discounts,
                ytd_fees=ytd_fees,
                ytd_users=ytd_users,
                ytd_new_users=ytd_new_users,
                mtd_sales=mtd_sales,
                mtd_profit=mtd_profit,
                mtd_lost=mtd_lost,
                mtd_dep=mtd_dep,
                mtd_dep_cash=mtd_dep_cash,
                mtd_dep_btc=mtd_dep_btc,
                mtd_dep_cc=mtd_dep_cc,
                mtd_discounts=mtd_discounts,
                mtd_fees=mtd_fees,
                mtd_users=mtd_users,
                mtd_new_users=mtd_new_users,
                graph_sales_day=views_data.create_dict('sales', 'day', 21),
                graph_deposits_day=graph_deposits_day,
                metrics=[metrics_2014],
                )

@view_config(route_name='admin_index_history',
             renderer='templates/admin/history.jinja2',
             permission='manage')
def admin_index_history(request):

    def metrics_per_time(start, end):
        xmas_start = start.replace(month=12, day=23)
        xmas_end = end.replace(month=1, day=2)

        metrics = {
            "sales":      Purchase.total(start=start, end=end),
            "profit":     PurchaseLineItem.profit_on_sales(start=start, end=end),
            "lost":       Inventory.total(start=start, end=end),
            "dep":        Deposit.total(start=start, end=end),
            "dep_cash":   CashDeposit.total(start=start, end=end),
            "dep_btc":    BTCDeposit.total(start=start, end=end),
            "dep_cc":     CCDeposit.total(start=start, end=end),
            "discounts":  Purchase.discounts(start=start, end=end),
            "fees":       Purchase.fees(start=start, end=end),
            "users":      Purchase.distinct(distinct_on=Event.user_id, start=start, end=end),
            "new_users":  User.get_number_new_users(start=start, end=end),
            "cashbox_lost":    Transaction.get_balance("lost", account.get_cash_account("cashbox"), start=start, end=end).balance,
            "safe_lost":       Transaction.get_balance("lost", account.get_cash_account("safe"), start=start, end=end).balance,
            "cashbox_found":   Transaction.get_balance("found", account.get_cash_account("cashbox"), start=start, end=end).balance,
            "safe_found":      Transaction.get_balance("found", account.get_cash_account("safe"), start=start, end=end).balance,
            "btcbox_lost":     Transaction.get_balance("lost", account.get_cash_account("btcbox"), start=start, end=end).balance,
            "btcbox_found":    Transaction.get_balance("found", account.get_cash_account("btcbox"), start=start, end=end).balance,
            "chezbetty_lost":  Transaction.get_balance("lost", account.get_cash_account("chezbetty"), start=start, end=end).balance,
            "chezbetty_found": Transaction.get_balance("found", account.get_cash_account("chezbetty"), start=start, end=end).balance,
            "store":           Transaction.get_balance("restock", account.get_cash_account("chezbetty"), start=start, end=end).balance,
            "donation":        Transaction.get_balance("donation", account.get_cash_account("chezbetty"), start=start, end=end).balance,
            "withdrawal":      Transaction.get_balance("withdrawal", account.get_cash_account("chezbetty"), start=start, end=end).balance,

            "weekend_sales":         Purchase.total(start=start, end=end, weekend_only=True),
            "weekday_sales":         Purchase.total(start=start, end=end, weekday_only=True),
            "business_hours_sales":  Purchase.total(start=start, end=end, weekday_only=True, business_hours_only=True),
            "business_full_sales":   Purchase.total(start=start, end=end, business_hours_only=True),
            "evening_hours_sales":   Purchase.total(start=start, end=end, evening_hours_only=True),
            "latenight_hours_sales": Purchase.total(start=start, end=end, latenight_hours_only=True),
            "ugos_closed_sales":     Purchase.total(start=start, end=end, ugos_closed_hours=True),
            "xmas_sales":            Purchase.total(start=xmas_start, end=xmas_end),
        }

        # Deposits is a rosy view. We must subtract what we didn't actually get
        deposits_lost = metrics["cashbox_lost"] + metrics["safe_lost"] + metrics["btcbox_lost"]
        deposits_net = metrics["dep"] - deposits_lost

        # Sometimes we find money. We need to add that to our donations
        other_donations = metrics["cashbox_found"] + metrics["safe_found"] + metrics["btcbox_found"] + metrics["chezbetty_found"]
        total_donations = metrics["donation"] + other_donations

        # It's possible we lose money magically. Note that
        other_withdrawals = metrics["chezbetty_lost"]
        total_withdrawals = metrics["withdrawal"] + other_withdrawals

        # Bookings: The amount of money that users have "committed to spend",
        # aka the money they've deposited to their user accounts
        bookings = deposits_net

        # Revenue: The amount of money that people have actually spent
        revenue = metrics['sales']

        # Deferred Revenue: Money that people have committed to spend that
        # Betty is holding that we have not yet spend (aka Bookings - Revenue).
        # This counts as a liability against Betty's gross assets on the balance sheet
        deferred_revenue = bookings - revenue




        net = revenue + total_donations - metrics["store"] - total_withdrawals - deferred_revenue

        metrics['bookings'] = bookings
        metrics['revenue'] = revenue
        metrics['deferred_revenue'] = deferred_revenue
        metrics["net"] = net

        return metrics


    # Calculate for all years
    start = 2014
    end = arrow.now().year

    metrics = []
    for i in range(start, end+1):
        metrics.append([i, metrics_per_time(arrow.get(i, 1, 1), arrow.get(i+1, 1, 1))])

    print(metrics)

    return {
        "metrics": metrics
    }


@view_config(route_name='admin_item_barcode_json',
             renderer='json',
             permission='manage')
def admin_item_barcode_json(request):
    try:
        item = Item.from_barcode(request.matchdict['barcode'])
        html = render('templates/admin/restock_row.jinja2', {'item': item, 'line': {}})
        return {'status': 'success',
                'type':   'item',
                'data':   html,
                'id':     item.id,
                'name':   item.name,
                'price':  float(item.price)}
    except NoResultFound:
        try:
            box = Box.from_barcode(request.matchdict['barcode'])
            html = render('templates/admin/restock_row.jinja2', {'box': box, 'line': {}})
            return {'status': 'success',
                    'type':   'box',
                    'data':   html,
                    'id':     box.id}
        except NoResultFound:
            return {'status': 'unknown_barcode'}
        except Exception as e:
            if request.debug:
                raise(e)
            else:
                return {'status': 'error'}


    except Exception as e:
        if request.debug:
            raise(e)
        else:
            return {'status': 'error'}


@view_config(route_name='admin_item_id_json',
             renderer='json',
             permission='manage')
def admin_item_id_json(request):
    try:
        item = Item.from_id(request.matchdict['id'])
        return {'status': 'success',
                'type':   'item',
                'id':     item.id,
                'name':   item.name,
                'price':  float(item.price)}

    except Exception as e:
        if request.debug:
            raise(e)
        else:
            return {'status': 'error'}


@view_config(route_name='admin_item_search_json',
             renderer='json',
             permission='manage')
def admin_item_search_json(request):
    try:
        boxes = Box.from_fuzzy(request.matchdict['search'])
        items = Item.from_fuzzy(request.matchdict['search'])
        box_vendors = BoxVendor.from_number_fuzzy(request.matchdict['search'])
        item_vendors = ItemVendor.from_number_fuzzy(request.matchdict['search'])

        ret = {'matches': []}

        for b in boxes:
            ret['matches'].append(('box', b.name, b.barcode, b.id, b.enabled, 0))

        for bv in box_vendors:
            ret['matches'].append(('box', bv.box.name, bv.box.barcode, bv.box.id, bv.box.enabled, 0))

        for i in items:
            ret['matches'].append(('item', i.name, i.barcode, i.id, i.enabled, i.in_stock))

        for iv in item_vendors:
            ret['matches'].append(('item', iv.item.name, iv.item.barcode, iv.item.id, iv.item.enabled, iv.item.in_stock))

        ret['status'] = 'success'

        return ret

    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error'}



@view_config(route_name='admin_user_search_json',
             renderer='json',
             permission='manage')
def admin_user_search_json(request):
    try:
        users = User.from_fuzzy(request.matchdict['search'], any=False)

        ret = {'matches': []}

        for u in users:
            ret['matches'].append({'id':       u.id,
                                   'name':     u.name,
                                   'uniqname': u.uniqname,
                                   'umid':     u.umid,
                                   'balance':  float(u.balance),
                                   'enabled':  u.enabled,
                                   'role':     u.role})

        ret['status'] = 'success'

        return ret

    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error'}



@view_config(route_name='admin_restock',
             renderer='templates/admin/restock.jinja2',
             permission='manage')
def admin_restock(request):
    restock_items = ''
    rows = 0
    global_cost = Decimal(0)
    donation = Decimal(0)
    reimbursees = Reimbursee.all()
    reimbursee_selected = 'none'
    if len(request.GET) != 0:
        for index,packed_values in request.GET.items():
            values = packed_values.split(',')
            if index == 'global_cost':
                try:
                    global_cost = round(Decimal(values[0] or 0), 2)
                except:
                    global_cost = Decimal(0)
            elif index == 'donation':
                try:
                    donation = round(Decimal(values[0] or 0), 2)
                except:
                    donation = Decimal(0)
            elif index == 'reimbursee':
                reimbursee_selected = values[0]
            else:
                line_values = {}
                line_type = values[0]
                line_id = int(values[1])
                line_values['quantity'] = int(values[2])
                line_values['wholesale'] = Decimal(values[3])
                line_values['coupon'] = Decimal(values[4] if values[4] != 'None' else 0)
                line_values['salestax'] = values[5] == 'True'
                line_values['btldeposit'] = values[6] == 'True'

                if line_type == 'item':
                    item = Item.from_id(line_id)
                    box = None
                elif line_type == 'box':
                    item = None
                    box = Box.from_id(line_id)

                restock_line = render('templates/admin/restock_row.jinja2',
                    {'item': item, 'box': box, 'line': line_values})
                restock_items += restock_line.replace('-X', '-{}'.format(index))
                rows += 1

    return {'items': Item.all_force(),
            'boxes': Box.all(),
            'restock_items': restock_items,
            'restock_rows': rows,
            'global_cost': global_cost,
            'donation': donation,
            'reimbursees': reimbursees,
            'reimbursee_selected': reimbursee_selected}


@view_config(route_name='admin_restock_submit',
             request_method='POST',
             permission='manage')
def admin_restock_submit(request):

    # Array of (Item, quantity, total) tuples
    items_for_pricing = []
    # Keep track of the total number of items being restocked. We use
    # this to divide up the "global cost" to each item.
    total_items_restocked = 0

    # Add an item to the array or update its totals
    def add_item(item, quantity, total):
        nonlocal total_items_restocked
        total_items_restocked += quantity
        for i in range(len(items_for_pricing)):
            if items_for_pricing[i][0].id == item.id:
                items_for_pricing[i][1] += quantity
                items_for_pricing[i][2] += total
                break
        else:
            items_for_pricing.append([item,quantity,total])

    # Arrays to pass to datalayer
    items = []

    # Check if we should update prices with this restock.
    # This is useful for updating old restocks without changing the price
    # of the current inventory.
    update_prices = True
    if 'restock-noprice' in request.POST:
        update_prices = False

    # Check for a global cost that should be applied across all items.
    # Note: this can be negative to reflect a discount of some kind applied to
    # all items.
    global_cost = Decimal(request.POST['restock-globalcost'] or 0)

    # Check for a global donation that should be given to chez betty and not
    # to the items in the restock.
    donation = Decimal(request.POST['restock-donation'] or 0)

    # Check who we should credit this restock to
    if request.POST['restock-reimbursee'] == 'none':
        reimbursee = None
    else:
        reimbursee = Reimbursee.from_id(int(request.POST['restock-reimbursee']))

    for key,val in request.POST.items():

        try:
            f = key.split('-')

            # Only look at the row when we get the id key
            if len(f) >= 2 and f[1] == 'id':

                obj_type   = request.POST['-'.join([f[0], 'type', f[2]])]
                obj_id     = request.POST['-'.join([f[0], 'id', f[2]])]
                quantity   = int(request.POST['-'.join([f[0], 'quantity', f[2]])] or 0)
                wholesale  = Decimal(request.POST['-'.join([f[0], 'wholesale', f[2]])] or 0)
                coupon     = Decimal(request.POST['-'.join([f[0], 'coupon', f[2]])] or 0)
                salestax   = request.POST['-'.join([f[0], 'salestax', f[2]])] == 'on'
                btldeposit = request.POST['-'.join([f[0], 'bottledeposit', f[2]])] == 'on'
                itemcount  = int(request.POST['-'.join([f[0], 'itemcount', f[2]])])

                # Skip this row if quantity is 0
                if quantity == 0:
                    continue
                elif quantity > 5000:
                    # Must be a typo
                    raise ValueError

                # Calculate the total
                total = quantity * (wholesale - coupon)
                if salestax:
                    total *= Decimal('1.06')
                if btldeposit:
                    total += (Decimal('0.10') * itemcount * quantity)
                total = round(total, 2)

                # Create arrays of restocked items/boxes
                if obj_type == 'item':
                    item = Item.from_id(obj_id)

                    # Set properties based on how it was restocked
                    item.bottle_dep = btldeposit
                    item.sales_tax = salestax

                    add_item(item, quantity, total)
                    items.append((item, quantity, total, wholesale, coupon, salestax, btldeposit))

                elif obj_type == 'box':
                    box = Box.from_id(obj_id)

                    # Set properties from restock
                    if update_prices:
                        box.wholesale = wholesale
                    box.bottle_dep = btldeposit
                    box.sales_tax = salestax

                    inv_cost = total / (box.subitem_count * quantity)
                    for itembox in box.items:
                        # Set subitem properties too
                        itembox.item.bottle_dep = btldeposit
                        itembox.item.sales_tax = salestax

                        subquantity = itembox.quantity * quantity
                        subtotal    = (itembox.percentage / 100) * total
                        add_item(itembox.item, subquantity, subtotal)

                    items.append((box, quantity, total, wholesale, coupon, salestax, btldeposit))

                else:
                    # don't know this item/box/?? type
                    continue

        except (ValueError, decimal.InvalidOperation):
            request.session.flash('Error parsing data for {}. Skipped.'.format(obj_id), 'error')
            continue
        except NoResultFound:
            request.session.flash('No {} with id {} found. Skipped.'.format(obj_type, obj_id), 'error')
            continue
        except ZeroDivisionError:
            # Ignore this line
            continue
        except Exception as e:
            if request.debug: raise(e)
            continue


    # Now that we've iterated all items to be restocked, calculate
    # how much we are going to add to the price of each item to make
    # up for the "global cost" (or discount).
    global_cost_item_addition = global_cost / total_items_restocked

    # Iterate the grouped items, update prices and wholesales, and then restock
    if update_prices:
        for item,quantity,total in items_for_pricing:
            if quantity == 0:
                request.session.flash('Error: Attempt to restock item {} with quantity 0. Item skipped.'.format(item), 'error')
                continue
            item.wholesale = round((total/quantity) + global_cost_item_addition, 4)
            # Set the item price
            if not item.sticky_price:
                item.price = round(item.wholesale * Decimal('1.15'), 2)

    if len(items) == 0:
        request.session.flash('Have to restock at least one item.', 'error')
        return HTTPFound(location=request.route_url('admin_restock'))

    try:
        if request.POST['restock-date']:
            restock_date = datetime.datetime.strptime(request.POST['restock-date'].strip(),
                '%Y/%m/%d %H:%M%z').astimezone(tz=pytz.timezone('UTC')).replace(tzinfo=None)
        else:
            restock_date = None
    except Exception as e:
        if request.debug: raise(e)
        # Could not parse date
        restock_date = None

    try:
        e = datalayer.restock(items, global_cost, donation, reimbursee, request.user, restock_date)
        request.session.flash('Restock complete.', 'success')
        return HTTPFound(location=request.route_url('admin_event', event_id=e.id))
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Restock failed because some error occurred.', 'error')
        return HTTPFound(location=request.route_url('admin_restock'))



@view_config(route_name='admin_cash_reconcile',
             renderer='templates/admin/cash_reconcile.jinja2',
             permission='manage')
def admin_cash_reconcile(request):
    return {}


@view_config(route_name='admin_cash_reconcile_submit',
             request_method='POST',
             permission='manage')
def admin_cash_reconcile_submit(request):
    try:

        if request.POST['cash-box-reconcile-type'] == 'cashboxtosafe':
            if account.get_cash_account("cashbox").balance == Decimal('0'):
                request.session.flash('Nothing to move!', 'error')
                return HTTPFound(location=request.route_url('admin_index'))

            else:
                event = datalayer.cashbox_to_safe(request.user)

                request.session.flash('Moved cashbox contents to safe.', 'success')
                return HTTPFound(location=request.route_url('admin_event', event_id=event.id))

        elif request.POST['cash-box-reconcile-type'] == 'safetobank':
            if request.POST['amount'].strip() == '':
                # We just got an empty string (and not 0)
                request.session.flash('Error: must enter an amount', 'error')
                return HTTPFound(location=request.route_url('admin_cash_reconcile'))

            amount = Decimal(request.POST['amount'])

            if request.POST['cash-box-reconcile'] == 'on':
                # Make the safe total to 0
                event = datalayer.reconcile_safe(amount, request.user)

                request.session.flash('Cash deposits reconciled successfully.', 'success')
                return HTTPFound(location=request.route_url('admin_event', event_id=event.id))
            else:
                # Just move some of the money
                event = datalayer.safe_to_bank(amount, request.user)

                request.session.flash('Moved ${:,.2f} from the safe to the bank'.format(amount), 'success')
                # return HTTPFound(location=request.route_url('admin_event'))
                return HTTPFound(location=request.route_url('admin_event', event_id=event.id))

    except decimal.InvalidOperation:
        request.session.flash('Error: Bad value for safe amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_reconcile'))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error occurred', 'error')
        return HTTPFound(location=request.route_url('admin_cash_reconcile'))


def admin_btc_reoncile(request):
    return {}

def admin_btc_reconcile_post(request):
    try:
        if request.POST['amount'].strip() == '':
            # We just got an empty string (and not 0)
            request.session.flash('Error: must enter an amount in the  box amount', 'error')
            return HTTPFound(location=request.route_url('admin_cash_reconcile'))

        amount = Decimal(request.POST['amount'])
        expected_amount = datalayer.reconcile_cash(amount, request.user)

        request.session.flash('Cash box recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_cash_reconcile_success',
            _query={'amount':amount, 'expected_amount':expected_amount}))

    except decimal.InvalidOperation:
        request.session.flash('Error: Bad value for cash box amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_reconcile'))


@view_config(route_name='admin_inventory',
             renderer='templates/admin/inventory.jinja2',
             permission='manage')
def admin_inventory(request):
    items1 = DBSession.query(Item)\
                      .filter(Item.enabled==True)\
                      .filter(Item.in_stock!=0)\
                      .order_by(Item.name).all()
    items2 = DBSession.query(Item)\
                      .filter(Item.enabled==True)\
                      .filter(Item.in_stock==0)\
                      .order_by(Item.name).all()
    items3 = DBSession.query(Item)\
                      .filter(Item.enabled==False)\
                      .order_by(Item.name).all()

    undone_inventory = {}
    if len(request.GET) != 0:
        undone_inventory
        for item_id,quantity_counted in request.GET.items():
            undone_inventory[int(item_id)] = int(quantity_counted)

    return {'items_have': items1,
            'items_donthave': items2,
            'items_disabled': items3,
            'undone_inventory': undone_inventory}


@view_config(route_name='admin_inventory_submit',
             request_method='POST',
             permission='manage')
def admin_inventory_submit(request):
    try:
        items = {}
        for key in request.POST:
            try:
                # Parse quantity first so we don't have to find the item if
                # we aren't recording an inventory.
                new_quantity = int(request.POST[key])
                item = Item.from_id(key.split('-')[2])
                items[item] = new_quantity
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
    except Exception as e:
        if request.debug: raise(e)
        return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_items_add',
             renderer='templates/admin/items_add.jinja2',
             permission='manage')
def admin_items_add(request):
    if len(request.GET) == 0:
        return {'d': {'item_count': 1}}
    else:
        return {'d': request.GET}


@view_config(route_name='admin_items_add_submit',
             request_method='POST',
             permission='manage')
def admin_items_add_submit(request):
    error_items = []

    # Iterate all the POST keys and find the ones that are item names
    for key in request.POST:
        kf = key.split('-')
        if len(kf) == 3 and kf[0] == 'item' and kf[2] == 'name':
            id = int(kf[1])
            stock = 0
            wholesale = 0
            price = 0
            enabled = False

            # Parse out the important fields looking for errors
            try:
                name = request.POST['item-{}-name'.format(id)].strip()
                name_general = request.POST['item-{}-general'.format(id)].strip()
                name_volume = request.POST['item-{}-volume'.format(id)].strip()
                barcode = request.POST['item-{}-barcode'.format(id)].strip()
                sales_tax = request.POST['item-{}-salestax'.format(id)].strip() == 'on'
                bottle_dep = request.POST['item-{}-bottledep'.format(id)].strip() == 'on'

                # Check that name and barcode are not blank. If name is blank
                # treat this as an empty row and skip. If barcode is blank
                # we will get a database error so send that back to the user.
                if name == '':
                    continue
                if barcode == '':
                    error_items.append({'name': name,
                                        'general': name_general,
                                        'volume': name_volume,
                                        'barcode': barcode,
                                        'salestax': sales_tax,
                                        'bottledep': bottle_dep})
                    request.session.flash('Error adding item: {}. No barcode.'.\
                                    format(name), 'error')
                    continue

                # Make sure the name and/or barcode doesn't already exist
                if Item.exists_name(name):
                    error_items.append({'name': name,
                                        'general': name_general,
                                        'volume': name_volume,
                                        'barcode': barcode,
                                        'salestax': sales_tax,
                                        'bottledep': bottle_dep})
                    request.session.flash('Error adding item: {}. Name exists.'.\
                                    format(name), 'error')
                    continue
                if barcode and Item.exists_barcode(barcode):
                    error_items.append({'name': name,
                                        'general': name_general,
                                        'volume': name_volume,
                                        'barcode': barcode,
                                        'salestax': sales_tax,
                                        'bottledep': bottle_dep})
                    request.session.flash('Error adding item: {}. Barcode exists.'.\
                                    format(name), 'error')
                    continue

                # Add the item to the DB
                item = Item(name, barcode, price, wholesale, sales_tax, bottle_dep, stock, enabled)
                DBSession.add(item)
                DBSession.flush()
                request.session.flash(
                        'Added <a href="/admin/item/edit/{}">{}</a>'.\
                                format(item.id, item.name),
                        'success')
            except Exception as e:
                if request.debug: raise(e)
                if len(name):
                    error_items.append({'name': name,
                                        'general': name_general,
                                        'volume': name_volume,
                                        'barcode': barcode,
                                        'salestax': sales_tax,
                                        'bottledep': bottle_dep})
                    request.session.flash('Error adding item: {}. Most likely a duplicate barcode.'.\
                                    format(name), 'error')
                # Otherwise this was probably a blank row; ignore.
    if len(error_items):
        flat = {}
        e_count = 0
        for err in error_items:
            for k,v in err.items():
                flat['item-{}-{}'.format(e_count, k)] = v
            e_count += 1
        flat['item_count'] = len(error_items)
        return HTTPFound(location=request.route_url('admin_items_add', _query=flat))
    else:
        return HTTPFound(location=request.route_url('admin_items_add'))


@view_config(route_name='admin_items_list',
             renderer='templates/admin/items_list.jinja2',
             permission='manage')
def admin_items_list(request):
    group = request.GET['group'] if 'group' in request.GET else 'active'

    if group == 'active':
        page  = 'active'
        items = Item.all()

        last_activity = {}

        # Calculate the number sold here (much faster)
        # Also calculate how much each sale was worth to us
        purchased_items = PurchaseLineItem.all()
        purchased_quantities = {}
        purchased_amount = {}
        for pi in purchased_items:
            if pi.item_id not in purchased_quantities:
                purchased_quantities[pi.item_id] = 0
            if pi.item_id not in purchased_amount:
                purchased_amount[pi.item_id] = 0

            purchased_quantities[pi.item_id] += pi.quantity
            purchased_amount[pi.item_id] += pi.amount

        # Calculate the number lost here (much faster)
        lost_items = InventoryLineItem.all()
        lost_quantities = {}
        for li in lost_items:
            if li.item_id not in lost_quantities:
                lost_quantities[li.item_id] = 0
            lost_quantities[li.item_id] += (li.quantity - li.quantity_counted)

        # Calculate the amount we have paid to the store for all items
        stocked_items = RestockLineItem.all()
        stocked_amount = {}
        for si in stocked_items:
            if si.item_id not in stocked_amount:
                stocked_amount[si.item_id] = 0
            stocked_amount[si.item_id] += si.amount

            if si.item_id not in last_activity:
                last_activity[si.item_id] = si.transaction.event.timestamp
            elif si.transaction.event.timestamp > last_activity[si.item_id]:
                last_activity[si.item_id] = si.transaction.event.timestamp

        stocked_boxes = RestockLineBox.all()
        for sb in stocked_boxes:
            for sbi in sb.box.items:
                if sbi.item_id not in stocked_amount:
                    stocked_amount[sbi.item_id] = 0
                try:
                    percentage = sbi.percentage / 100
                except:
                    percentage = 0
                stocked_amount[sbi.item_id] += (percentage * sb.amount)

                if sbi.item_id not in last_activity:
                    last_activity[sbi.item_id] = sb.transaction.event.timestamp
                elif sb.transaction.event.timestamp > last_activity[sbi.item_id]:
                    last_activity[sbi.item_id] = sb.transaction.event.timestamp

        # Get the sale speed
        sale_speeds = views_data.item_sale_speed(30)

        # Get the total amount of inventory we have
        inventory_total = Item.total_inventory_wholesale()

        now = arrow.now()

        for item in items:
            if item.id in purchased_quantities:
                item.number_sold = purchased_quantities[item.id]
            else:
                item.number_sold = None

            if item.id in lost_quantities:
                item.number_lost = lost_quantities[item.id]
            else:
                item.number_lost = None

            if item.id in sale_speeds:
                speed = sale_speeds[item.id]

                item.sale_speed_thirty_days = speed

                if speed > 0:
                    item.days_until_out = item.in_stock / sale_speeds[item.id]
                elif item.in_stock <= 0:
                    item.days_until_out = 0
                else:
                    item.days_until_out = None
            else:
                item.sale_speed_thirty_days = 0
                item.days_until_out = None

            item.inventory_percent = ((item.wholesale * item.in_stock) / inventory_total) * 100

            # Calculate "theftiness" which is:
            #
            #                number stolen
            #  theftiness = ---------------
            #                 number sold
            #
            if not item.number_sold:
                if not item.number_lost or item.number_lost < 0:
                    # Both 0, just put this at 0.
                    item.theftiness = 0.0
                else:
                    # Haven't sold any, but at least one stolen. Bad!
                    item.theftiness = 100.0
            else:
                item.theftiness = ((item.number_lost or 0.0)/item.number_sold) * 100.0


            # Calculate profit which is:
            #
            #  profit = (num_sold * price) - ((num_purchased - num_in_stock) * wholesale)
            #
            # Note: this is not perfect for two reasons.
            #       1. when calculating how much we paid to the store for each item
            #          in a box, we use the current box division percents, not
            #          necessarily the ones used when we restocked the box.
            #       2. We just use the current wholesale price for calculating
            #          how much we have in stock. This may not be the same as what
            #          we actually paid. Therefore, this will only be correct when
            #          stock==0.
            if item.id not in stocked_amount:
                stocked_amount[item.id] = 0
            if item.id not in purchased_amount:
                purchased_amount[item.id] = 0
            item.profit = purchased_amount[item.id] - (stocked_amount[item.id] - (item.wholesale * item.in_stock))

            # Record the most recent activity of the item
            if item.id not in last_activity:
                item.last_activity = None
            else:
                item.last_activity = (now - last_activity[item.id]).days


    else:
        items = Item.disabled()
        page  = 'disabled'

         # Keep track of items which are in stock but disabled.
        items_stocked_but_disabled = []

        for item in items:
            if item.in_stock != 0 and item.enabled == False:
                items_stocked_but_disabled.append(item)

        # Show a warning to the admin if we have any items in stock but that people
        # can't buy
        if len(items_stocked_but_disabled) > 0:
            err = 'Items '
            err += ' '.join(['"{}",'.format(i.name) for i in items_stocked_but_disabled])
            err = err[0:-1]
            err += ' are stocked but marked disabled.'
            request.session.flash(err, 'error')

    return {'items': items,
            'items_page': page}


@view_config(route_name='admin_item_edit',
             renderer='templates/admin/item_edit.jinja2',
             permission='manage')
def admin_item_edit(request):
    try:
        try:
            purchase_limit = request.GET['purchase_limit']
            if purchase_limit.lower() == 'none':
                purchase_limit = None
            else:
                purchase_limit = int(purchase_limit)
        except KeyError:
            purchase_limit = 10
        try:
            event_limit = request.GET['event_limit']
            if event_limit.lower() == 'none':
                event_limit = None
            else:
                event_limit = int(event_limit)
        except KeyError:
            event_limit = 5

        item = Item.from_id(request.matchdict['item_id'])
        vendors = Vendor.all()

        purchases, purchases_total = SubTransaction.all_item_purchases(item.id,
                limit=purchase_limit, count=True)
        if purchase_limit is None or purchases_total <= purchase_limit:
            purchases_total = None

        events, events_total = SubTransaction.all_item_events(item.id,
                limit=event_limit, count=True)
        sst, sst_total = SubSubTransaction.all_item(item.id,
                limit=event_limit, count=True)

        def sortTransactionsByEvent(t):
            try:
                return t.event.timestamp
            except:
                pass
            try:
                return t.transaction.event.timestamp
            except:
                pass
            try:
                return t.subtransaction.transaction.event.timestamp
            except:
                pass

        events.extend(sst)
        events.sort(key=sortTransactionsByEvent, reverse=True)
        events_total += sst_total

        if event_limit is None or events_total <= event_limit:
            events_total = None
        else:
            events = events[:event_limit]

        stats = {}
        stats['stock'] = item.in_stock

        stats['num_sold'] = 0
        stats['sold_amount'] = 0
        purchased_items = PurchaseLineItem.all_item(item.id)
        for pi in purchased_items:
            stats['num_sold'] += pi.quantity
            stats['sold_amount'] += pi.amount

        stats['stocked_amount'] = 0
        stocked_items = RestockLineItem.all_item(item.id)
        for si in stocked_items:
            stats['stocked_amount'] += si.amount
        # XXX PERF
        stocked_boxes = RestockLineBox.all()
        for sb in stocked_boxes:
            for sbi in sb.box.items:
                if sbi.item_id == item.id:
                    try:
                        percentage = sbi.percentage / 100
                    except:
                        percentage = 0.0
                    stats['stocked_amount'] += (percentage * sb.amount)

        stats['sale_speed'] = views_data.item_sale_speed(30, item.id)

        if stats['sale_speed'] > 0:
            stats['until_out'] = item.in_stock / stats['sale_speed']
        elif item.in_stock <= 0:
            stats['until_out'] = 0
        else:
            stats['until_out'] = '---'

        stats['lost'] = 0
        lost_items = InventoryLineItem.all_item(item.id)
        for li in lost_items:
            stats['lost'] += (li.quantity - li.quantity_counted)

        inventory_total = Item.total_inventory_wholesale()
        stats['inv_percent'] = ((item.wholesale * item.in_stock) / inventory_total) * 100

        # Theftiness
        if stats['num_sold'] == 0:
            if stats['lost'] <= 0:
                stats['theftiness'] = 0.0
            else:
                stats['theftiness'] = 100.0
        else:
            stats['theftiness'] = (stats['lost']/stats['num_sold']) * 100.0

        # Profit
        stats['profit'] = stats['sold_amount'] - (stats['stocked_amount'] - (item.wholesale * item.in_stock))

        # Don't display vendors that already have an item number in the add
        # new vendor item number section
        used_vendors = []
        for vendoritem in item.vendors:
            used_vendors.append(vendoritem.vendor_id)
        new_vendors = []
        for vendor in vendors:
            if vendor.id not in used_vendors and vendor.enabled:
                new_vendors.append(vendor)

        can_delete = False
        if datalayer.can_delete_item(item):
            can_delete = True

        # Tags
        other_tags = []
        all_tags = Tag.all()
        for tag in all_tags:
            for it in item.tags:
                if it.tag.id == tag.id:
                    break
            else:
                other_tags.append(tag)

        return {'item': item,
                'can_delete': can_delete,
                'vendors': vendors,
                'new_vendors': new_vendors,
                'purchases': purchases,
                'purchases_total': purchases_total,
                'purchase_limit': purchase_limit,
                'events': events,
                'events_total': events_total,
                'event_limit': event_limit,
                'stats': stats,
                'other_tags': other_tags}
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Unable to find item {}'.format(request.matchdict['item_id']), 'error')
        return HTTPFound(location=request.route_url('admin_items_edit'))


@view_config(route_name='admin_item_edit_submit',
             request_method='POST',
             permission='manage')
def admin_item_edit_submit(request):
    try:
        item = Item.from_id(int(request.POST['item-id']))

        for key in request.POST:
            fields = key.split('-')
            if fields[1] == 'vendor' and fields[2] == 'id':
                # Handle the vendor item numbers
                vendor_id = int(request.POST['item-vendor-id-'+fields[3]])
                item_num  = request.POST['item-vendor-item_num-'+fields[3]].strip()

                for vendoritem in item.vendors:
                    # Update the VendorItem record.
                    # If the item num is blank, set the record to disabled
                    # and do not update the item number.
                    if vendoritem.vendor_id == vendor_id and vendoritem.enabled:
                        if item_num == '':
                            vendoritem.enabled = False
                        else:
                            vendoritem.item_number = item_num
                        break
                else:
                    if item_num != '':
                        # Add a new vendor to the item
                        vendor = Vendor.from_id(vendor_id)
                        item_vendor = ItemVendor(vendor, item, item_num)
                        DBSession.add(item_vendor)

            else:
                # Update the base item
                field = fields[1]
                if field == 'price':
                    val = round(Decimal(request.POST[key]), 2)
                elif field == 'wholesale':
                    val = round(Decimal(request.POST[key]), 4)
                elif field == 'barcode':
                    val = request.POST[key].strip() or None
                elif field == 'img':
                    try:
                        ifile = request.POST[key].file
                        ifile.seek(0)
                        im = Image.open(ifile)
                        buf = io.BytesIO()
                        im.save(buf, 'jpeg')
                        buf.seek(0)
                        try:
                            item.img.img = buf.read()
                        except AttributeError:
                            buf.seek(0)
                            item_img = ItemImage(item.id, buf.read())
                            item.img = item_img
                    except AttributeError:
                        # No image uploaded, skip
                        pass
                    continue
                else:
                    val = request.POST[key].strip()

                setattr(item, field, val)

        DBSession.flush()
        request.session.flash('Item updated successfully.', 'success')
        return HTTPFound(location=request.route_url('admin_item_edit', item_id=int(request.POST['item-id'])))

    except NoResultFound:
        request.session.flash('Error when updating product.', 'error')
        return HTTPFound(location=request.route_url('admin_items_edit'))

    except IntegrityError:
        request.session.flash('Error updating item. Probably conflicting barcodes.', 'error')
        return HTTPFound(location=request.route_url('admin_item_edit', item_id=int(request.POST['item-id'])))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error processing item fields. {}'.format(e), 'error')
        return HTTPFound(location=request.route_url('admin_item_edit', item_id=int(request.POST['item-id'])))


@view_config(route_name='admin_item_barcode_pdf', permission='manage')
def admin_item_barcode_pdf(request):
    try:
        item = Item.from_id(request.matchdict['item_id'])
        fname = '/tmp/{}.pdf'.format(item.id)

        c = canvas.Canvas(fname, pagesize=letter)

        barcode_height = .250*inch

        x_margin = 0.27 * inch
        y_margin = 0.485 * inch

        x_interlabel = 0.12 * inch
        y_interlabel = 0

        x_label = 1.5 * inch
        y_label = 1 * inch

        label_padding = 0.1 * inch

        x = x_margin
        y = letter[1] - y_margin

        # Don't know why I need this, but it makes it work
        x_hack = 0.2 * inch

        if item.barcode:
            label_text = item.barcode
        else:
            for bi in item.boxes:
                if len(bi.box.items) == 1:
                    label_text = bi.box.barcode
                    break
            else:
                request.session.flash('Cannot create barcodes. \
                    This item has no barcode and none of the boxes it is in\
                    only have one item.', 'error')
                return HTTPFound(location=request.route_url('admin_item_edit', item_id=request.matchdict['item_id']))

        def len_fn(t):
            print('len_fn {} -- {}'.format(t, c.stringWidth(t, "Helvetica", 8)))
            return c.stringWidth(t, "Helvetica", 8)
        try:
            abbr = abbreviate.Abbreviate()
            name = abbr.abbreviate(item.name, target_len=1.3*inch, len_fn=len_fn)
        except Exception as e:
            # A little extra robustness here since this library is really alpha
            name = item.name

        barcode = code93.Extended93(label_text)
        print(barcode.minWidth())
        print(barcode.minWidth() / inch)

        for x_ind in range(5):
            for y_ind in range(10):
                x_off = x + x_ind * (x_label + x_interlabel) + label_padding - x_hack
                y_off = y - y_ind * (y_label + y_interlabel) - barcode_height - label_padding

                print("x_off {} ({}) y_off {} ({})".format(x_off, x_off / inch, y_off, y_off / inch))

                barcode = code93.Extended93(label_text)
                barcode.drawOn(c, x_off, y_off)

                x_text = x_off + 6.4 * mm
                y_text = y_off - 5 * mm
                c.setFont("Helvetica", 12)
                c.drawString(x_text, y_text, label_text)

                y_text = y_text - 5 * mm
                c.setFont("Helvetica", 8)
                c.drawString(x_text, y_text, name)

        c.showPage()
        c.save()

        response = FileResponse(fname, request=request)
        return response
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error occurred while creating barcodes.', 'error')
        return HTTPFound(location=request.route_url('admin_item_edit', item_id=request.matchdict['item_id']))


@view_config(route_name='admin_item_delete', permission='admin')
def admin_item_delete(request):
    try:
        item = Item.from_id(int(request.matchdict['item_id']))
        if datalayer.can_delete_item(item):
            datalayer.delete_item(item)
            request.session.flash('Item has been deleted', 'success')
            return HTTPFound(location=request.route_url('admin_items_edit'))
        else:
            request.session.flash('Item has dependencies. It cannot be deleted.', 'error')
            return HTTPFound(location=request.route_url('admin_item_edit', item_id=item.id))
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error occurred while deleting item.', 'error')
        return HTTPFound(location=request.route_url('admin_items_edit'))


################################################################################
# BAD SCANS
################################################################################

@view_config(route_name='admin_badscans_list',
             renderer='templates/admin/badscans.jinja2',
             permission='manage')
def admin_badscans_list(request):
    badscans = BadScan.get_scans_with_counts()

    return {'badscans': badscans}


################################################################################
# TAGS
################################################################################

@view_config(route_name='admin_tags_list',
             renderer='templates/admin/tags_list.jinja2',
             permission='manage')
def admin_tags_list(request):
    tags = Tag.all()

    return {'tags': tags}


@view_config(route_name='admin_box_add',
             renderer='templates/admin/boxes_add.jinja2',
             permission='manage')
def admin_box_add(request):
    items = Item.all_force()

    if len(request.GET) == 0:
        fields = {'subitem_count': 1}
    else:
        fields = request.GET

    return {'items': items,
            'vendors': Vendor.all(),
            'd': fields}


@view_config(route_name='admin_box_add_submit',
             request_method='POST',
             permission='manage')
def admin_box_add_submit(request):
    try:
        error = False
        items_empty_barcode = 0

        # Work on the box first
        box_name      = request.POST['box-name'].strip()
        box_barcode   = request.POST['box-barcode'].strip()
        box_salestax  = request.POST['box-sales_tax'] == 'on'
        box_bottledep = request.POST['box-bottle_dep'] == 'on'
        box_vendor    = int(request.POST['box-vendor'])
        box_itemnum   = request.POST['box-vendor-item_num'].strip()

        if box_name == '':
            request.session.flash('Error adding box: must have name.', 'error')
            error = True
        elif Box.exists_name(box_name):
            request.session.flash('Error adding box: name "{}" already exists.'.format(box_name), 'error')
            error = True
        if box_barcode == '':
            request.session.flash('Error adding box: must have barcode.', 'error')
            error = True
        elif Box.exists_barcode(box_barcode):
            request.session.flash('Error adding box: barcode "{}" already exists.'.format(box_barcode), 'error')
            error = True

        # Now iterate over the subitems
        items_to_add = []
        total_items = 0

        for key in request.POST:
            kf = key.split('-')
            if kf[0] == 'box' and kf[1] == 'item' and kf[3] == 'item':
                # Found the select. We will use this to iterate through the
                # lines
                row_id = int(kf[2])
                item_id = request.POST['box-item-{}-item'.format(row_id)]
                if item_id == '':
                    # This was a blank row that was skipped for some reason
                    continue

                quantity = request.POST['box-item-{}-quantity'.format(row_id)]
                try:
                    quantity = int(quantity)
                except:
                    request.session.flash('Error adding subitem: quantity must be numeric.', 'error')
                    error = True

                total_items += quantity

                if item_id == 'new':
                    # Need to add a new item for this box
                    item_name     = request.POST['box-item-{}-name'.format(row_id)].strip()
                    item_barcode  = request.POST['box-item-{}-barcode'.format(row_id)].strip()

                    if item_barcode == '':
                        items_empty_barcode += 1

                    if Item.exists_name(item_name):
                        request.session.flash('Error adding item: name "{}" already exists.'.format(item_name), 'error')
                        items_to_add.append((Item.from_name(item_name), quantity))
                    if item_barcode and Item.exists_barcode(item_barcode):
                        request.session.flash('Error adding item: barcode "{}" already exists.'.format(item_barcode), 'error')
                        items_to_add.append((Item.from_barcode(item_barcode), quantity))
                    else:
                        items_to_add.append(({'name': item_name,
                                              'barcode': item_barcode}, quantity))
                else:
                    # Just add the specified item to the box
                    item = Item.from_id(int(item_id))
                    if item.barcode == '':
                        items_empty_barcode += 1
                    items_to_add.append((item, quantity))

        if items_empty_barcode > 0 and len(items_to_add) > 1:
            request.session.flash('Error adding box: If an item doesn\'t have a barcode there can only be one subitem in the box', 'error')
            error = True

        # At this point we have parsed all of the data from the web form
        if error:
            # Somewhere we encountered an error
            # Need to refill the forms and tell the user that they messed up
            err = {}
            for k,v in request.POST.items():
                err[k] = v
            err['subitem_count'] = row_id + 1
            return HTTPFound(location=request.route_url('admin_box_add', _query=err))

        else:
            # Need to create the box
            box = Box(box_name, box_barcode, box_bottledep, box_salestax)
            DBSession.add(box)
            DBSession.flush()
            request.session.flash(
                    'Added box: <a href="/admin/box/edit/{}">{}</a>'.\
                            format(box.id, box.name),
                    'success')

            # Need to add items to the box
            for item,quantity in items_to_add:
                if type(item) is dict:
                    # Need to add this item first
                    item = Item(name=item['name'],
                                barcode=item['barcode'] or None,
                                price=0,
                                wholesale=0,
                                sales_tax=box_salestax,
                                bottle_dep=box_bottledep,
                                in_stock=0,
                                enabled=False)
                    DBSession.add(item)
                    DBSession.flush()
                    request.session.flash(
                            'Added item: <a href="/admin/item/edit/{}">{}</a>'.\
                                    format(item.id, item.name),
                            'success')

                # Set the box percentages all equal
                box_item = BoxItem(box, item, quantity, round((quantity/total_items)*100, 2))
                DBSession.add(box_item)

            if box_itemnum != '':
                # Add a new vendor to the item
                vendor = Vendor.from_id(box_vendor)
                box_vendor = BoxVendor(vendor, box, box_itemnum)
                DBSession.add(box_vendor)

            # Leave this in addition to the creation message above in case some
            # part of the box failed to add, attention needs to be drawn
            request.session.flash('Box "{}" added successfully.'.format(box_name), 'success')
            return HTTPFound(location=request.route_url('admin_box_add'))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error occurred.', 'error')
        return HTTPFound(location=request.route_url('admin_box_add'))


@view_config(route_name='admin_boxes_edit',
             renderer='templates/admin/boxes_edit.jinja2',
             permission='manage')
def admin_boxes_edit(request):
    unpopulated_boxes = []
    active_populated = []
    inactive_populated = []

    boxes_active = Box.get_enabled()
    boxes_inactive = Box.get_disabled()

    for box in boxes_active:
        if box.subitem_count == 0:
            unpopulated_boxes.append(box)
        else:
            active_populated.append(box)

    for box in boxes_inactive:
        if box.subitem_count == 0:
            unpopulated_boxes.append(box)
        else:
            inactive_populated.append(box)

    boxes = active_populated + inactive_populated
    return {'boxes': boxes, 'unpopulated': unpopulated_boxes}


@view_config(route_name='admin_boxes_edit_submit',
             request_method='POST',
             permission='manage')
def admin_boxes_edit_submit(request):
    updated = set()
    for key in request.POST:
        try:
            box = Box.from_id(int(key.split('-')[2]))
        except:
            request.session.flash('No box with ID {}.  Skipped.'.format(key.split('-')[2]), 'error')
            continue
        name = box.name
        try:
            field = key.split('-')[1]
            if field == 'wholesale':
                val = round(Decimal(request.POST[key]), 2)
            else:
                val = request.POST[key].strip()

            setattr(box, field, val)
            DBSession.flush()
        except ValueError:
            # Could not parse wholesale as float
            request.session.flash('Error updating {}'.format(name), 'error')
            continue
        except:
            DBSession.rollback()
            request.session.flash('Error updating {} for {}.  Skipped.'.\
                    format(key.split('-')[1], name), 'error')
            continue
        updated.add(box.id)
    if len(updated):
        count = len(updated)
        #request.session.flash('{} box{} properties updated successfully.'.format(count, ['s',''][count==1]), 'success')
        request.session.flash('boxes updated successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_boxes_edit'))


@view_config(route_name='admin_box_edit',
             renderer='templates/admin/box_edit.jinja2',
             permission='manage')
def admin_box_edit(request):
    try:
        box = Box.from_id(request.matchdict['box_id'])
        items = Item.all_force()

        # Don't display items that already have an item number in the add
        # new item section
        used_items = []
        for boxitem in box.items:
            used_items.append(boxitem.item_id)
        new_items = []
        for item in items:
            if item.id not in used_items:
                new_items.append(item)

        vendors = Vendor.all()
        # Don't display vendors that already have an item number in the add
        # new vendor item number section
        used_vendors = []
        for vendorbox in box.vendors:
            used_vendors.append(vendorbox.vendor_id)
        new_vendors = []
        for vendor in vendors:
            if vendor.id not in used_vendors and vendor.enabled:
                new_vendors.append(vendor)

        can_delete = False
        if datalayer.can_delete_box(box):
            can_delete = True

        return {'box': box,
                'items': items,
                'can_delete': can_delete,
                'new_items': new_items,
                'new_vendors': new_vendors}
    except NoResultFound:
        request.session.flash('Unable to find Box {}'.format(request.matchdict['box_id']), 'error')
        return HTTPFound(location=request.route_url('admin_boxes_edit'))
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error editing box', 'error')
        return HTTPFound(location=request.route_url('admin_boxes_edit'))


@view_config(route_name='admin_box_edit_submit',
             request_method='POST',
             permission='manage')
def admin_box_edit_submit(request):
    try:
        box = Box.from_id(int(request.POST['box-id']))

        for key in request.POST:
            fields = key.split('-')
            if fields[1] == 'item' and fields[2] == 'id':
                # Handle the sub item quantities
                item_id  = int(request.POST['box-item-id-'+fields[3]])
                quantity = request.POST['box-item-quantity-'+fields[3]].strip()
                percentage = request.POST['box-item-percentage-'+fields[3]].strip()

                for boxitem in box.items:
                    # Update the BoxItem record.
                    # If the item quantity is zero or blank, set the record to
                    # disabled and do not update the quantity.
                    if boxitem.item_id == item_id and boxitem.enabled:
                        if quantity == '' or int(quantity) == 0:
                            boxitem.enabled = False
                        else:
                            boxitem.quantity = int(quantity)
                            boxitem.percentage = round(Decimal(percentage), 2)
                        break
                else:
                    if quantity != '':
                        # Add a new vendor to the item
                        item = Item.from_id(item_id)
                        box_item = BoxItem(box, item, quantity, round(Decimal(percentage), 2))
                        DBSession.add(box_item)

            elif fields[1] == 'vendor' and fields[2] == 'id':
                # Handle the vendor item numbers
                vendor_id = int(request.POST['box-vendor-id-'+fields[3]])
                item_num  = request.POST['box-vendor-item_num-'+fields[3]].strip()

                for vendorbox in box.vendors:
                    # Update the VendorItem record.
                    # If the item num is blank, set the record to disabled
                    # and do not update the item number.
                    if vendorbox.vendor_id == vendor_id and vendorbox.enabled:
                        if item_num == '':
                            vendorbox.enabled = False
                        else:
                            vendorbox.item_number = item_num
                        break
                else:
                    if item_num != '':
                        # Add a new vendor to the item
                        vendor = Vendor.from_id(vendor_id)
                        box_vendor = BoxVendor(vendor, box, item_num)
                        DBSession.add(box_vendor)

            else:
                # Update the base item
                field = fields[1]
                if field == 'wholesale':
                    val = round(Decimal(request.POST[key]), 2)
                elif field == 'quantity':
                    val = int(request.POST[key])
                elif field == 'sales_tax':
                    val = request.POST[key] == 'on'
                elif field == 'bottle_dep':
                    val = request.POST[key] == 'on'
                else:
                    val = request.POST[key].strip()

                setattr(box, field, val)

        DBSession.flush()
        request.session.flash('Box updated successfully.', 'success')
        return HTTPFound(location=request.route_url('admin_box_edit', box_id=int(request.POST['box-id'])))

    except NoResultFound:
        request.session.flash('Error when updating box.', 'error')
        return HTTPFound(location=request.route_url('admin_boxes_edit'))

    except ValueError:
        request.session.flash('Error processing box fields.', 'error')
        return HTTPFound(location=request.route_url('admin_box_edit', box_id=int(request.POST['box-id'])))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error updating box.', 'error')
        return HTTPFound(location=request.route_url('admin_box_edit', box_id=int(request.POST['box-id'])))


@view_config(route_name='admin_box_delete', permission='admin')
def admin_box_delete(request):
    try:
        box = Box.from_id(int(request.matchdict['box_id']))
        if datalayer.can_delete_box(box):
            datalayer.delete_box(box)
            request.session.flash('Box has been deleted', 'success')
            return HTTPFound(location=request.route_url('admin_boxes_edit'))
        else:
            request.session.flash('Box has dependencies. It cannot be deleted.', 'error')
            return HTTPFound(location=request.route_url('admin_box_edit', box_id=box.id))
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error occurred while deleting box.', 'error')
        return HTTPFound(location=request.route_url('admin_boxes_edit'))


################################################################################
# VENDORS
################################################################################

@view_config(route_name='admin_vendors_edit',
             renderer='templates/admin/vendors_edit.jinja2',
             permission='manage')
def admin_vendors_edit(request):
    vendors_active = DBSession.query(Vendor).filter_by(enabled=True).order_by(Vendor.name).all()
    vendors_inactive = DBSession.query(Vendor).filter_by(enabled=False).order_by(Vendor.name).all()
    vendors = vendors_active + vendors_inactive
    return {'vendors': vendors}


@view_config(route_name='admin_vendors_edit_submit',
             request_method='POST',
             permission='manage')
def admin_vendors_edit_submit(request):

    # Group all the form items into a nice dict that we can cleanly iterate
    vendors = {}
    for key in request.POST:
        fields = key.split('-')
        if fields[2] not in vendors:
            vendors[fields[2]] = {}
        vendors[fields[2]][fields[1]] = request.POST[key].strip()

    for vendor_id, vendor_props in vendors.items():
        if vendor_id == 'new':
            if vendor_props['name'] == '':
                # Don't add blank vendors
                continue
            vendor = Vendor(vendor_props['name'])
            DBSession.add(vendor)
        else:
            vendor = Vendor.from_id(int(vendor_id))
            for prop_name, prop_val in vendor_props.items():
                setattr(vendor, prop_name, prop_val)

    request.session.flash('Vendors updated successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_vendors_edit'))


################################################################################
# REIMBURSEES
################################################################################

@view_config(route_name='admin_reimbursees',
             renderer='templates/admin/reimbursees.jinja2',
             permission='manage')
def admin_reimbursees(request):
    reimbursees = Reimbursee.all()
    return {'reimbursees': reimbursees}


@view_config(route_name='admin_reimbursees_add_submit',
             request_method='POST',
             permission='manage')
def admin_reimbursees_add_submit(request):

    new_reimbursee_name = request.POST['reimbursee-name-new'].strip()
    new_reimbursee = Reimbursee(new_reimbursee_name)

    DBSession.add(new_reimbursee)
    DBSession.flush()

    request.session.flash('Reimbursee added successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_reimbursees'))


@view_config(route_name='admin_reimbursees_reimbursement_submit',
             request_method='POST',
             permission='manage')
def admin_reimbursees_reimbursement_submit(request):
    try:
        reimbursee = Reimbursee.from_id(int(request.POST['reimbursee']))
        amount = Decimal(request.POST['amount'])
        notes = request.POST['notes']

        # Check that we are not trying to reimburse too much
        if amount > reimbursee.balance:
            request.session.flash('Error: Cannot reimburse more than user is owed.', 'error')
            return HTTPFound(location=request.route_url('admin_reimbursees'))

        # Check that we are not trying to reimburse a negative amount
        if amount <= 0:
            request.session.flash('Error: Cannot reimburse zero or a negative amount.', 'error')
            return HTTPFound(location=request.route_url('admin_reimbursees'))

        # Look for custom date
        try:
            if request.POST['reimbursement-date']:
                event_date = datetime.datetime.strptime(request.POST['reimbursement-date'].strip(),
                    '%Y/%m/%d %H:%M%z').astimezone(tz=pytz.timezone('UTC')).replace(tzinfo=None)
            else:
                event_date = None
        except Exception as e:
            if request.debug: raise(e)
            # Could not parse date
            event_date = None

        e = datalayer.add_reimbursement(amount, notes, reimbursee, request.user, event_date)

        request.session.flash('Reimbursement recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_event', event_id=e.id))

    except decimal.InvalidOperation:
        request.session.flash('Error: Bad value for reimbursement amount', 'error')
        return HTTPFound(location=request.route_url('admin_reimbursees'))
    except:
        request.session.flash('Error: Unable to add reimbursement', 'error')
        return HTTPFound(location=request.route_url('admin_reimbursees'))


################################################################################
# USERS
################################################################################

@view_config(route_name='admin_users_list',
             renderer='templates/admin/users_list.jinja2',
             permission='admin')
def admin_users_list(request):
    user_group = request.GET['group'] if 'group' in request.GET else 'active'

    if user_group == 'active':
        users = User.get_normal_users()
        page  = 'active'
    elif user_group == 'archived':
        users = User.get_archived_users()
        page  = 'archived'
    else:
        users = User.get_disabled_users()
        page  = 'disabled'

    roles = {'user': 'User',
             'serviceaccount': 'Service Account',
             'manager': 'Manager',
             'administrator': 'Administrator'}
    return {'users': users,
            'user_page': page,
            'roles': roles}


@view_config(route_name='admin_users_stats',
             renderer='templates/admin/users_stats.jinja2',
             permission='admin')
def admin_users_stats(request):
    normal_users = User.get_normal_users()
    archived_users = User.get_archived_users()
    disabled_users = User.get_disabled_users()
    roles = {'user': 'User',
             'serviceaccount': 'Service Account',
             'manager': 'Manager',
             'administrator': 'Administrator'}
    return {'normal_users': normal_users,
            'archived_users': archived_users,
            'disabled_users': disabled_users,
            'user_page': 'stats',
            'roles': roles}


@view_config(route_name='admin_uniqname',
             permission='admin')
def admin_uniqname(request):
    try:
        user = User.from_uniqname(request.matchdict['uniqname'], local_only=True)
        return HTTPFound(location=request.route_url('admin_user', user_id=user.id))
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('No user with that uniqname.', 'error')
        return HTTPFound(location=request.route_url('admin_index'))

@view_config(route_name='admin_user',
             renderer='templates/admin/user.jinja2',
             permission='admin')
def admin_user(request):
    try:
        user = User.from_id(request.matchdict['user_id'])

        transactions,count = limitable_request(
                request, user.get_transactions, limit=20, count=True)

        events, events_total = limitable_request(
                request, user.get_events, prefix='event', limit=10, count=True)

        my_pools = Pool.all_by_owner(user)
        return {'user': user,
                'events': events,
                'events_total': events_total,
                'my_pools': my_pools}
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Invalid user?', 'error')
        return HTTPFound(location=request.route_url('admin_index'))

@view_config(route_name='admin_user_details',
             renderer='templates/admin/user_details.jinja2',
             permission='admin')
def admin_user_details(request):
    try:
        user = User.from_id(request.matchdict['user_id'])
        details = user.get_details()
        return details
    except InvalidUserException:
        return {'notice': 'User no longer in the directory.'}
    except Exception as e:
        if request.debug: raise(e)
        return {'notice': 'Unknown error loading user detail.'}

@view_config(route_name='admin_user_purchase_add',
             renderer='templates/admin/user_purchase_add.jinja2',
             permission='admin')
def admin_user_purchase_add(request):
    return {}


@view_config(route_name='admin_user_purchase_add_submit',
             request_method='POST',
             permission='admin')
def admin_user_purchase_add_submit(request):
    try:
        # Get the user from the POST data
        user = User.from_id(int(request.POST['user-search-choice']))

        # Get the deposit amount (if any)
        try:
            deposit_amount = Decimal(request.POST['user-purchase-add-deposit'])
        except Exception:
            deposit_amount = Decimal(0)

        if deposit_amount < 0:
            request.session.flash('Cannot deposit a negative amount.', 'error')
            return HTTPFound(location=request.route_url('admin_user_purchase_add'))

        # Group all of the items into the correct structure
        items = {}
        for key,value in request.POST.items():
            fields = key.split('-')
            if len(fields) == 6:
                # Make sure that we are adding an item
                if fields[4] == 'item':
                    item_id = int(fields[5])
                    quantity = int(value)

                    if quantity > 0:
                        item = Item.from_id(item_id)
                        items[item] = quantity

        if len(items) == 0 and deposit_amount == 0:
            # Nothing to purchase or deposit?
            request.session.flash('Must buy at least one item or make a deposit.', 'error')
            return HTTPFound(location=request.route_url('admin_user_purchase_add'))

        response_string = ''

        if len(items) > 0:
            # Commit the purchase
            purchase = datalayer.purchase(user, user, items)
            response_string += 'Purchase added. Event ID: <a href="/admin/event/{0}">{0}</a>.'.format(purchase.event.id)

        if deposit_amount > 0:
            # Add the deposit
            deposit = datalayer.deposit(user, user, deposit_amount, False)
            response_string += ' Deposit added. Event ID: <a href="/admin/event/{0}">{0}</a>.'.format(deposit['event'].id)

        request.session.flash(response_string, 'success')
        return HTTPFound(location=request.route_url('admin_user_purchase_add'))
    except NoResultFound:
        request.session.flash('Invalid user?', 'error')
        return HTTPFound(location=request.route_url('admin_user_purchase_add'))
    except KeyError:
        request.session.flash('Did you select a user?', 'error')
        return HTTPFound(location=request.route_url('admin_user_purchase_add'))


@view_config(route_name='admin_user_balance_edit',
             renderer='templates/admin/user_balance_edit.jinja2',
             permission='admin')
def admin_user_balance_edit(request):
    return {}


@view_config(route_name='admin_user_balance_edit_submit',
             request_method='POST',
             permission='admin')
def admin_user_balance_edit_submit(request):
    try:
        if request.POST['sender-search-choice'] == 'chezbetty':
            sender = 'chezbetty'
        else:
            sender = User.from_id(int(request.POST['sender-search-choice']))
        if request.POST['recipient-search-choice'] == 'chezbetty':
            recipient = 'chezbetty'
        else:
            recipient = User.from_id(int(request.POST['recipient-search-choice']))

        # Can't both be betty
        if sender == 'chezbetty' and recipient == 'chezbetty':
            request.session.flash('At least one of sender/recipient must not be betty.', 'error')
            return HTTPFound(location=request.route_url('admin_user_balance_edit'))

        amount = Decimal(request.POST['amount'])
        reason = request.POST['reason'].strip()

        event = None
        if sender == 'chezbetty' or recipient == 'chezbetty':
            # This boils down to just a user balance update
            if recipient == 'chezbetty':
                # Need to flip the sign
                amount *= -1
                user = sender
            else:
                user = recipient
            event = datalayer.adjust_user_balance(user, amount, reason, request.user)

        else:
            # This is a transfer between two people.
            # Maybe someday we'd support that transaction directly, but
            # we don't have a transaction type for that right now, so we
            # just use betty as a middle man
            event = datalayer.transfer_user_money(sender, recipient, amount, reason, request.user)

        request.session.flash('User(s) account updated.', 'success')
        return HTTPFound(location=request.route_url('admin_event', event_id=event.id))
    except NoResultFound:
        request.session.flash('Invalid user?', 'error')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))
    except decimal.InvalidOperation:
        request.session.flash('Invalid adjustment amount.', 'error')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))
    except __event.NotesMissingException:
        request.session.flash('Must include a reason', 'error')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))
    except KeyError:
        request.session.flash('Must select a sender and recipient', 'error')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error', 'error')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))

@view_config(route_name='admin_user_password_create',
             renderer='json',
             permission='admin')
def admin_user_password_create(request):
    try:
        user = User.from_id(int(request.matchdict['user_id']))
        if user.has_password:
            return {'status': 'error',
                    'msg': 'Error: User already has password.'}
        user_password_reset(user)
        return {'status': 'success',
                'msg': 'Password set and emailed to user.'}
    except NoResultFound:
        return {'status': 'error',
                'msg': 'Could not find user.'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error',
                'msg': 'Error.'}

@view_config(route_name='admin_user_password_reset',
        renderer='json',
        permission='admin')
def admin_user_password_reset(request):
    try:
        user = User.from_id(int(request.matchdict['user_id']))
        user_password_reset(user)
        return {'status': 'success',
                'msg': 'Password set and emailed to user.'}
    except NoResultFound:
        return {'status': 'error',
                'msg': 'Could not find user.'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error',
                'msg': 'Error.'}


# Method for de-activating users who haven't used Betty in a while.
# This lets us handle users who don't go to north anymore or who
# have graduated.
#
# The balance they have when they are archived is recorded and then any
# balance or debt is moved to the chezbetty account. If the user ever does
# return, their old balance is restored.
@view_config(route_name='admin_user_archive',
        renderer='json',
        permission='admin')
def admin_user_archive(request):
    try:
        user = User.from_id(int(request.matchdict['user_id']))

        # Cannot archive already archived user
        if user.archived:
            return {'status': 'error',
                    'msg': 'User already archived.'}

        # Save current balance
        user.archived_balance = user.balance

        # Now transfer it to chezbetty if there is anything to transfer
        if user.balance != 0:
            datalayer.adjust_user_balance(user,
                                          user.balance*-1,
                                          'Archived user who has not used Betty in a while.',
                                          request.user)

        # Mark it done
        user.archived = True

        return {'status': 'success',
                'msg': 'User achived.'}
    except NoResultFound:
        return {'status': 'error',
                'msg': 'Could not find user.'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error',
                'msg': 'Error.'}


# AJAX for changing user role
@view_config(route_name='admin_user_changerole',
        renderer='json',
        permission='admin')
def admin_user_changerole(request):
    try:
        user = User.from_id(int(request.matchdict['user_id']))
        new_role = request.matchdict['role']

        user.role = new_role

        return {'status': 'success',
                'msg': 'User role successfully changed to {}.'.format(new_role)}
    except NoResultFound:
        return {'status': 'error',
                'msg': 'Could not find user.'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error',
                'msg': 'Error.'}


@view_config(route_name='admin_users_email',
             renderer='templates/admin/users_email.jinja2',
             permission='admin')
def admin_users_email(request):
    return {'users': User.all(),
            'emails_suppressed': suppress_emails()}


@view_config(route_name='admin_users_email_endofsemester',
             request_method='POST',
             permission='admin')
def admin_users_email_endofsemester(request):
    threshold = float(request.POST['threshold'])
    if threshold < 0:
        request.session.flash('Threshold should be >= 0', 'error')
        return HTTPFound(location=request.route_url('admin_users_email'))
    # Work around storing balances as floats so we don't bug people with -$0.00
    if threshold < 0.01:
        threshold = 0.01
    deadbeats = DBSession.query(User).\
            filter(User.enabled).\
            filter(User.balance < -threshold).\
            all()
    for deadbeat in deadbeats:
        send_email(
                TO=deadbeat.uniqname+'@umich.edu',
                SUBJECT='Chez Betty Balance',
                body=render('templates/admin/email_endofsemester.jinja2',
                    {'user': deadbeat})
                )

    request.session.flash('{} user(s) with balances under {} emailed.'.\
            format(len(deadbeats), threshold), 'success')
    return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_users_email_deadbeats',
             request_method='POST',
             permission='admin')
def admin_users_email_deadbeats(request):
    deadbeats = User.get_deadbeats()
    for deadbeat in deadbeats:
        send_email(
                TO=deadbeat.uniqname+'@umich.edu',
                SUBJECT='Chez Betty Balance',
                body=render('templates/admin/email_deadbeats.jinja2',
                    {'user': deadbeat})
                )

    request.session.flash('Deadbeat users emailed.', 'success')
    return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_users_email_oneperson',
             request_method='POST',
             permission='admin')
def admin_users_email_oneperson(request):
    user = User.from_id(int(request.POST['user']))
    to = user.uniqname+'@umich.edu'

    send_email(
            TO       = to,
            SUBJECT  = request.POST['subject'],
            body     = request.POST['body'],
            encoding = request.POST['encoding'],
            )

    request.session.flash('E-mail sent to ' + to, 'success')
    return HTTPFound(location=request.route_url('admin_users_email'))


@view_config(route_name='admin_users_email_all',
             request_method='POST',
             permission='admin')
def admin_users_email_all(request):
    users = User.all()

    send_bcc_email(
            BCC='@umich.edu, '.join(map(lambda x: x.uniqname, users)) + '@umich.edu',
            SUBJECT  = request.POST['subject'],
            body     = request.POST['body'],
            encoding = request.POST['encoding'],
            )

    request.session.flash('All users emailed.', 'success')
    return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_pools',
             renderer='templates/admin/pools.jinja2',
             permission='admin')
def admin_pools(request):
    return {'pools': Pool.all()}


@view_config(route_name='admin_pool',
             renderer='templates/admin/pool.jinja2',
             permission='admin')
def admin_pool(request):
    try:
        pool = Pool.from_id(request.matchdict['pool_id'])

        events, events_total = limitable_request(
                request, pool.get_events, prefix='event', limit=10, count=True)

        return {'pool': pool,
                'pool_owner': User.from_id(pool.owner),
                'users': User.all(),
                'events': events,
                'events_total': events_total}
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Unable to find pool.', 'error')
        return HTTPFound(location=request.route_url('admin_pools'))

@view_config(route_name='admin_pool_name',
             request_method='POST',
             renderer='json',
             permission='admin')
def admin_pool_name(request):
    pool = Pool.from_id(int(request.POST['pool']))
    pool.name = request.POST['name']

    return {
            'status': 'success',
            'msg': 'Pool name updated successfully.',
            'value': request.POST['name'],
            }

@view_config(route_name='admin_pool_addmember_submit',
             request_method='POST',
             permission='admin')
def admin_pool_addmember_submit(request):
    try:
        pool = Pool.from_id(request.POST['pool-id'])

        # Look up the user that is being added to the pool
        user = User.from_id(request.POST['user_id'])

        # Can't add yourself
        if user.id == pool.owner:
            request.session.flash('Cannot add owner to a pool.', 'error')
            return HTTPFound(location=request.route_url('admin_pool', pool_id=pool.id))

        # Make sure the user isn't already in the pool
        for u in pool.users:
            if u.user_id == user.id:
                request.session.flash('User is already in pool.', 'error')
                return HTTPFound(location=request.route_url('admin_pool', pool_id=pool.id))

        # Add the user to the pool
        pooluser = PoolUser(pool, user)
        DBSession.add(pooluser)
        DBSession.flush()

        request.session.flash('{} added to the pool.'.format(user.name), 'succcess')
        return HTTPFound(location=request.route_url('admin_pool', pool_id=pool.id))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error adding user to pool.', 'error')
        return HTTPFound(location=request.route_url('admin_pools'))


################################################################################
# CASH
################################################################################

@view_config(route_name='admin_cash_donation',
             renderer='templates/admin/cash_donation.jinja2',
             permission='admin')
def admin_cash_donation(request):
    return {}


@view_config(route_name='admin_cash_donation_submit',
             request_method='POST',
             permission='admin')
def admin_cash_donation_submit(request):
    try:
        amount = Decimal(request.POST['amount'])

        # Look for custom date
        try:
            if request.POST['donation-date']:
                event_date = datetime.datetime.strptime(request.POST['donation-date'].strip(),
                    '%Y/%m/%d %H:%M%z').astimezone(tz=pytz.timezone('UTC')).replace(tzinfo=None)
            else:
                event_date = None
        except Exception as e:
            if request.debug: raise(e)
            # Could not parse date
            event_date = None

        e = datalayer.add_donation(amount, request.POST['notes'], request.user, event_date)

        request.session.flash('Donation recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_event', event_id=e.id))

    except decimal.InvalidOperation:
        request.session.flash('Error: Bad value for donation amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_donation'))
    except event.NotesMissingException:
        request.session.flash('Error: Must include a donation reason', 'error')
        return HTTPFound(location=request.route_url('admin_cash_donation'))
    except:
        request.session.flash('Error: Unable to add donation', 'error')
        return HTTPFound(location=request.route_url('admin_cash_donation'))


@view_config(route_name='admin_cash_withdrawal',
             renderer='templates/admin/cash_withdrawal.jinja2',
             permission='admin')
def admin_cash_withdrawal(request):
    reimbursees = Reimbursee.all()
    return {'reimbursees': reimbursees}


@view_config(route_name='admin_cash_withdrawal_submit',
             request_method='POST',
             permission='admin')
def admin_cash_withdrawal_submit(request):
    try:
        amount = Decimal(request.POST['amount'])
        reimbursee = Reimbursee.from_id(int(request.POST['reimbursee']))

        # Look for custom date
        try:
            if request.POST['withdrawal-date']:
                event_date = datetime.datetime.strptime(request.POST['withdrawal-date'].strip(),
                    '%Y/%m/%d %H:%M%z').astimezone(tz=pytz.timezone('UTC')).replace(tzinfo=None)
            else:
                event_date = None
        except Exception as e:
            if request.debug: raise(e)
            # Could not parse date
            event_date = None

        e = datalayer.add_withdrawal(amount, request.POST['notes'], reimbursee, request.user, event_date)

        request.session.flash('Withdrawal recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_event', event_id=e.id))

    except decimal.InvalidOperation:
        request.session.flash('Error: Bad value for withdrawal amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_withdrawal'))
    except event.NotesMissingException:
        request.session.flash('Error: Must include a withdrawal reason', 'error')
        return HTTPFound(location=request.route_url('admin_cash_withdrawal'))
    except:
        request.session.flash('Error: Unable to add withdrawal', 'error')
        return HTTPFound(location=request.route_url('admin_cash_withdrawal'))


@view_config(route_name='admin_cash_adjustment',
             renderer='templates/admin/cash_adjustment.jinja2',
             permission='admin')
def admin_cash_adjustment(request):
    return {}


@view_config(route_name='admin_cash_adjustment_submit',
             request_method='POST',
             permission='admin')
def admin_cash_adjustment_submit(request):
    try:
        amount = Decimal(request.POST['amount'])
        datalayer.reconcile_misc(amount, request.POST['notes'], request.user)

        request.session.flash('Adjustment recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_index'))

    except decimal.InvalidOperation:
        request.session.flash('Error: Bad value for adjustment amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_adjustment'))
    except event.NotesMissingException:
        request.session.flash('Error: Must include a adjustment reason', 'error')
        return HTTPFound(location=request.route_url('admin_cash_adjustment'))
    except:
        request.session.flash('Error: Unable to add adjustment', 'error')
        return HTTPFound(location=request.route_url('admin_cash_adjustment'))


@view_config(route_name='admin_btc_reconcile',
             renderer='templates/admin/btc_reconcile.jinja2',
             permission='admin')
def admin_btc_reconcile(request):
    try:
        btc_balance = Bitcoin.get_balance()
        btc = {"btc": btc_balance,
               "usd": btc_balance * Bitcoin.get_spot_price()}
    except BTCException:
        btc = {"btc": None,
               "usd": 0.0}
    btcbox = get_cash_account("btcbox")

    try:
        request.GET.getone("verbose")
        verbose = True
    except KeyError:
        verbose = False

    deposits = DBSession.query(BTCDeposit).order_by(desc(BTCDeposit.id)).all()
    cur_height = Bitcoin.get_block_height()

    transactions = []
    txhashes = {}
    for d in deposits:
        txhash = d.btctransaction
        if (verbose):
            btc_tx = Bitcoin.get_tx_by_hash(txhash)
            confirmations = (cur_height - btc_tx["block_height"] + 1) if "block_height" in btc_tx else 0

            true_amount = Decimal(0) # satoshis
            for output in btc_tx['out']:
                if output['addr'] == d.address and output['type'] == 0:
                    true_amount += Decimal(output['value'])

            true_amount /= 100000000  # bitcoins
        else:
            true_amount = d.amount_btc
            confirmations = '-'

        txhashes[txhash] = True

        transactions.append({'deposit' : d,
                      'mbtc' : round(d.amount_btc*1000, 2),
                      'true_amount' : true_amount,
                      'true_amount_mbtc' : round(true_amount*1000, 2),
                      'confirmations': confirmations})


    missed_deposits = []
    pending = DBSession.query(BtcPendingDeposit).order_by(desc(BtcPendingDeposit.id)).all()
    addrs = []
    for pend in pending:
        addrs.append(pend.address)


    if not(verbose):
        return {'btc': btc, 'btcbox': btcbox, 'deposits': deposits, 'transactions': transactions, 'missed' : missed_deposits}

    res = Bitcoin.get_tx_from_addrs('|'.join(addrs))
    if 'txs' in res:
        for tx in res['txs']:
            confirmations = (cur_height - tx['block_height'] + 1) if 'block_height' in tx else 0
            txhash = tx['hash']
            if txhash not in txhashes:
                # we found a btc deposit on the blockchain we didn't get a callback for!

                amount = Decimal(0)
                addr = None
                for output in tx['out']:
                    if output['addr'] in addrs and output['type'] == 0:
                        addr = output['addr']
                        amount += Decimal(output['value'])

                if addr is None:
                    # one of our pending addresses must have been a tx _input_;
                    # this is just coinbase moving coins out from under us...
                    # hopefully we can still redeem them though (!)
                    # (cold storage? fractional reserve? theft? time will tell!)
                    continue


                amount /= 100000000

                print("txhash=%s, addr=%s, txout:%s" % (txhash, addr, tx['out']))
                pending_deposit = DBSession.query(BtcPendingDeposit).filter(BtcPendingDeposit.address==addr).one()

                user = User.from_id(pending_deposit.user_id)  # from_id?
                missed_deposits.append({'txhash': txhash,
                                        'address': addr,
                                        'amount_btc' : amount,
                                        'amount_mbtc' : round(amount*1000, 2),
                                        'amount_usd' : amount * Bitcoin.get_spot_price(),
                                        'confirmations' : confirmations,
                                        'user': user})

    return {'btc': btc, 'btcbox': btcbox, 'deposits': deposits, 'transactions': transactions, 'missed' : missed_deposits}


@view_config(route_name='admin_btc_reconcile_submit',
             request_method='POST',
             permission='admin')
def admin_btc_reconcile_submit(request):
    try:
        #bitcoin_amount = Bitcoin.get_balance()
        btcbox = get_cash_account("btcbox")
        bitcoin_amount = Decimal(request.POST['amount_btc'])
        usd_amount = Decimal(request.POST['amount_usd'])
        bitcoin_available = Bitcoin.get_balance()

        #if (bitcoin_available < bitcoin_amount):
            # Not enough BTC in coinbase
            #request.session.flash('Error: cannot convert %s BTC, only %s BTC in account' % (bitcoin_amount, bitcoin_available), 'error')
            #return HTTPFound(location=request.route_url('admin_btc_reconcile'))

        # HACK: FIXME: what we really want here is the amount of bitcoins available in coinbase _before_ you did the sale
        # this kind of works, but is racy with users that deposit more. Then the math will just be fucked.
        # ultimate fix is to just use the coinbase sell api. I FUCKING WISH COINBASE HAD A WAY TO DO DEV ACCOUNTS!!!! WHAT ARE YOU GUYS
        # EVEN DOING OVER THERE?!?!?!
        bitcoin_available += bitcoin_amount

        #bitcoin_usd = Bitcoin.convert(bitcoin_amount)

        # we are taking ((bitcoin_amount)/(bitcoin_available)) of our bitcoins;
        # we should also expect bitcoin_usd to be that*btcbox.balance
        expected_usd = Decimal(math.floor(100*((bitcoin_amount*btcbox.balance) / bitcoin_available))/100)

        datalayer.reconcile_bitcoins(usd_amount, request.user, expected_amount=expected_usd)
        request.session.flash('Converted %s Bitcoins to %s USD' % (bitcoin_amount, usd_amount), 'success')
    except Exception as e:
        raise e
        #print(e)
        #request.session.flash('Error converting bitcoins', 'error')

    return HTTPFound(location=request.route_url('admin_index'))


def _get_event_filter_function(event_filter):
    fields = event_filter.split(':')
    if fields[0] == 'type':
        def filterfn (*args, **kwargs):
            return Event.get_events_by_type(fields[1], *args, **kwargs)
        return filterfn
    elif fields[0] == 'status':
        if fields[1] == 'deleted':
            return Event.get_deleted_events
    elif fields[0] == 'cash_account':
        def filterfn (*args, **kwargs):
            return Event.get_events_by_cashaccount(int(fields[1]), *args, **kwargs)
        return filterfn
    else:
        return Event.all


@view_config(route_name='admin_events',
             renderer='templates/admin/events.jinja2',
             permission='admin')
def admin_events(request):
    event_filter = request.GET['filter'] if 'filter' in request.GET else 'all'
    fn = _get_event_filter_function(event_filter)
    events = limitable_request(request, fn, limit=50)
    return {'events': events, 'event_filter': event_filter}


@view_config(route_name='admin_events_load_more',
             request_method='POST',
             renderer='json',
             permission='admin')
def admin_events_load_more(request):
    LIMIT = 100
    last  = int(request.POST['last'])

    fn = _get_event_filter_function(request.POST['filter'])
    events = fn(limit=LIMIT, offset=last)

    events_html = []
    for e in events:
        events_html.append(render('templates/admin/events_row.jinja2', {'event': e}))

    return {
            'count': last+LIMIT,
            'rows': events_html
            }


@view_config(route_name='admin_event',
             renderer='templates/admin/event.jinja2',
             permission='manage')
def admin_event(request):
    try:
        e = Event.from_id(int(request.matchdict['event_id']))
        if datalayer.can_undo_event(e):
            undo = '/admin/event/undo/{}'.format(e.id)
            return {'event': e, 'undo_url': undo}
        else:
            return {'event': e}
    except ValueError:
        request.session.flash('Invalid event ID', 'error')
        return HTTPFound(location=request.route_url('admin_events'))
    except:
        request.session.flash('Could not find event ID#{}'\
            .format(request.matchdict['event_id']), 'error')
        return HTTPFound(location=request.route_url('admin_events'))


@view_config(route_name='admin_event_upload',
             permission='manage')
def admin_event_upload(request):
    try:
        event = Event.from_id(int(request.POST['event-id']))
        receipt = request.POST['event-receipt'].file
        datalayer.upload_receipt(event, request.user, receipt)
        return HTTPFound(location=request.route_url('admin_event',
                         event_id=int(request.POST['event-id'])))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error {}'.format(e), 'error')
        return HTTPFound(location=request.route_url('admin_events'))


@view_config(route_name='admin_event_receipt',
             permission='manage')
def admin_event_receipt(request):
    try:
        receipt = Receipt.from_id(int(request.matchdict['receipt_id']))
        fname = '/tmp/{}.pdf'.format(uuid.uuid4())
        f = open(fname, 'wb')
        f.write(receipt.receipt)
        f.close()

        return FileResponse(fname, request=request)

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error', 'error')
        return HTTPFound(location=request.route_url('admin_events'))


@view_config(route_name='admin_event_undo',
             permission='admin')
def admin_event_undo(request):
    try:
        # Lookup the transaction that the user wants to undo
        event = Event.from_id(request.matchdict['event_id'])

        # Make sure its not already deleted
        if event.deleted:
            request.session.flash('Error: transaction already deleted', 'error')
            return HTTPFound(location=request.route_url('admin_events'))

        # Make sure we support undoing that type of transaction
        if not datalayer.can_undo_event(event):
            request.session.flash('Error: Cannot undo that type of transaction.', 'error')
            return HTTPFound(location=request.route_url('admin_events'))

        # If the checks pass, actually revert the transaction
        line_items = datalayer.undo_event(event, request.user)
        request.session.flash('Event successfully reverted.', 'success')

        if event.type == 'restock':
            return HTTPFound(location=request.route_url('admin_restock', _query=line_items))
        elif event.type == 'inventory':
            return HTTPFound(location=request.route_url('admin_inventory', _query=line_items))
        else:
            return HTTPFound(location=request.route_url('admin_events'))

    except NoResultFound:
        request.session.flash('Error: Could not find event to undo.', 'error')
        return HTTPFound(location=request.route_url('admin_events'))
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error: Failed to undo transaction.', 'error')
        return HTTPFound(location=request.route_url('admin_events'))



@view_config(route_name='admin_password_edit',
             renderer='templates/admin/password_edit.jinja2',
             permission='manage')
def admin_password_edit(request):
    return {}


@view_config(route_name='admin_password_edit_submit',
             request_method='POST',
             permission='manage')
def admin_password_edit_submit(request):
    pwd0 = request.POST['edit-password-0']
    pwd1 = request.POST['edit-password-1']
    if pwd0 != pwd1:
        request.session.flash('Error: Passwords do not match', 'error')
        return HTTPFound(location=request.route_url('admin_password_edit'))
    request.user.password = pwd0
    request.session.flash('Password changed successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_index'))
    # check that changing password for actually logged in user


@view_config(route_name='admin_requests',
             renderer='templates/admin/requests.jinja2',
             permission='admin')
def admin_requests(request):
    requests = Request.all()
    return {'requests': requests}


@view_config(route_name='admin_item_request_post_new',
             request_method='POST',
             permission='admin')
def item_request_post_new(request):
    try:
        item_request = Request.from_id(request.matchdict['id'])
        post_text = request.POST['post']
        if post_text.strip() == '':
            request.session.flash('Empty comment not saved.', 'error')
            return HTTPFound(location=request.route_url('admin_requests'))
        post = RequestPost(item_request, request.user, post_text, staff_post=True)
        DBSession.add(post)
        DBSession.flush()
    except Exception as e:
        if request.debug:
            raise(e)
        else:
            print(e)
        request.session.flash('Error posting comment.', 'error')
    return HTTPFound(location=request.route_url('admin_requests'))


@view_config(route_name='admin_announcements_edit',
             renderer='templates/admin/announcements_edit.jinja2',
             permission='admin')
def admin_announcements_edit(request):
    announcements = Announcement.all()
    return {'announcements': announcements}


@view_config(route_name='admin_announcements_edit_submit',
             request_method='POST',
             permission='admin')
def admin_announcements_edit_submit(request):

    # Group all the form items into a nice dict that we can cleanly iterate
    announcements = {}
    for key in request.POST:
        fields = key.split('-')
        if fields[2] not in announcements:
            announcements[fields[2]] = {}
        announcements[fields[2]][fields[1]] = request.POST[key].strip()

    for announcement_id, props in announcements.items():
        if announcement_id == 'new':
            if props['text'] == '':
                # Don't add blank announcements
                continue
            announcement = Announcement(request.user, props['text'])
            DBSession.add(announcement)
        else:
            announcement = Announcement.from_id(int(announcement_id))
            announcement.announcement = props['text']

    request.session.flash('Announcements updated successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_announcements_edit'))


@view_config(route_name='admin_tweet_submit',
             request_method='POST',
             permission='admin')
def admin_tweet_submit(request):

    message = request.POST['tweet']

    twitterapi = twitter.Twitter(auth=twitter.OAuth(
        request.registry.settings['twitter.access_token'],
        request.registry.settings['twitter.access_token_secret'],
        request.registry.settings['twitter.api_key'],
        request.registry.settings['twitter.api_secret']))

    twitterapi.statuses.update(status=message)

    request.session.flash('Tweeted successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_announcements_edit'))
