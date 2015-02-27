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
from .models.item import Item, ItemImage
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
from .models.tag import Tag
from .models.item_tag import ItemTag

from .utility import send_email

from .jinja2_filters import format_currency

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException

# Used for generating barcodes
from reportlab.graphics.barcode import code39
from reportlab.graphics.barcode import code93
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas

import abbreviate
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
    if event['renderer_name'] != 'json':
        count = {}
        count['items']        = Item.count()
        count['boxes']        = Box.count()
        count['vendors']      = Vendor.count()
        count['users']        = User.count()
        count['transactions'] = Transaction.count()
        count['restocks']     = Transaction.count("restock")
        count['requests']     = Request.count()
        count['pools']        = Pool.count()
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

@view_config(route_name='admin_ajax_bool', permission='admin')
def admin_ajax_bool(request):
    obj_str = request.matchdict['object']
    obj_id  = int(request.matchdict['id'])
    obj_field = request.matchdict['field']
    obj_state = request.matchdict['state'].lower() == 'true'

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
        request.response.set_cookie(obj_field, '1' if obj_state else '0')
        return request.response
    else:
        # Return an error, object type not recognized
        request.response.status = 502
        return request.response


    setattr(obj, obj_field, obj_state)

    DBSession.flush()

    return request.response

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
    items_low_stock = DBSession.query(Item)\
                               .filter(Item.enabled == True)\
                               .filter(Item.in_stock < 10)\
                               .order_by(Item.in_stock)\
                               .limit(5).all()
    users_shame     = DBSession.query(User)\
                               .filter(User.balance < 0)\
                               .order_by(User.balance)\
                               .limit(5).all()
    users_balance   = User.get_users_total()
    held_for_users  = User.get_amount_held()
    owed_by_users   = User.get_amount_owed()
    bsi             = DBSession.query(func.sum(PurchaseLineItem.quantity).label('quantity'), Item)\
                               .join(Item)\
                               .join(Transaction)\
                               .join(Event)\
                               .filter(Transaction.type=='purchase')\
                               .filter(Event.deleted==False)\
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

    cashbox_net = cashbox_found.balance - cashbox_lost.balance
    btcbox_net = btcbox_found.balance - btcbox_lost.balance
    chezbetty_net = chezbetty_found.balance - chezbetty_lost.balance

    total_sales          = Purchase.total()
    profit_on_sales      = PurchaseLineItem.profit_on_sales()
    total_inventory_lost = Inventory.total()
    total_deposits       = Deposit.total()
    total_cash_deposits  = CashDeposit.total()
    total_btc_deposits   = BTCDeposit.total()


    now = datetime.date.today()

    ytd_sales    = Purchase.total(views_data.ftz(datetime.date(now.year, 1, 1)), None)
    ytd_profit   = PurchaseLineItem.profit_on_sales(views_data.ftz(datetime.date(now.year, 1, 1)), None)
    ytd_lost     = Inventory.total(views_data.ftz(datetime.date(now.year, 1, 1)), None)
    ytd_dep      = Deposit.total(views_data.ftz(datetime.date(now.year, 1, 1)), None)
    ytd_dep_cash = CashDeposit.total(views_data.ftz(datetime.date(now.year, 1, 1)), None)
    ytd_dep_btc  = BTCDeposit.total(views_data.ftz(datetime.date(now.year, 1, 1)), None)

    mtd_sales    = Purchase.total(views_data.ftz(datetime.date(now.year, now.month, 1)), None)
    mtd_profit   = PurchaseLineItem.profit_on_sales(views_data.ftz(datetime.date(now.year, now.month, 1)), None)
    mtd_lost     = Inventory.total(views_data.ftz(datetime.date(now.year, now.month, 1)), None)
    mtd_dep      = Deposit.total(views_data.ftz(datetime.date(now.year, now.month, 1)), None)
    mtd_dep_cash = CashDeposit.total(views_data.ftz(datetime.date(now.year, now.month, 1)), None)
    mtd_dep_btc  = BTCDeposit.total(views_data.ftz(datetime.date(now.year, now.month, 1)), None)

    today_sales    = Purchase.total(views_data.ftz(datetime.date(now.year, now.month, now.day)), None)
    today_profit   = PurchaseLineItem.profit_on_sales(views_data.ftz(datetime.date(now.year, now.month, now.day)), None)
    today_lost     = Inventory.total(views_data.ftz(datetime.date(now.year, now.month, now.day)), None)
    today_dep      = Deposit.total(views_data.ftz(datetime.date(now.year, now.month, now.day)), None)
    today_dep_cash = CashDeposit.total(views_data.ftz(datetime.date(now.year, now.month, now.day)), None)
    today_dep_btc  = BTCDeposit.total(views_data.ftz(datetime.date(now.year, now.month, now.day)), None)


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


    return dict(events=events,
                items_low_stock=items_low_stock,
                users_shame=users_shame,
                users_balance=users_balance,
                held_for_users=held_for_users,
                owed_by_users=owed_by_users,
                cashbox=cashbox,
                btcbox=btcbox,
                chezbetty_cash=chezbetty_cash,
                chezbetty=chezbetty,
                cashbox_net=cashbox_net,
                btcbox_net=btcbox_net,
                chezbetty_net=chezbetty_net,
                restock=restock,
                donation=donation,
                withdrawal=withdrawal,
                inventory=inventory,
                best_selling_items=bsi,
                total_sales=total_sales,
                profit_on_sales=profit_on_sales,
                total_inventory_lost=total_inventory_lost,
                total_deposits=total_deposits,
                total_cash_deposits=total_cash_deposits,
                total_btc_deposits=total_btc_deposits,
                ytd_sales=ytd_sales,
                ytd_profit=ytd_profit,
                ytd_lost=ytd_lost,
                ytd_dep=ytd_dep,
                ytd_dep_cash=ytd_dep_cash,
                ytd_dep_btc=ytd_dep_btc,
                mtd_sales=mtd_sales,
                mtd_profit=mtd_profit,
                mtd_lost=mtd_lost,
                mtd_dep=mtd_dep,
                mtd_dep_cash=mtd_dep_cash,
                mtd_dep_btc=mtd_dep_btc,
                today_sales=today_sales,
                today_profit=today_profit,
                today_lost=today_lost,
                today_dep=today_dep,
                today_dep_cash=today_dep_cash,
                today_dep_btc=today_dep_btc,
                graph_items_day=views_data.create_dict('items', 'day', 21),
                graph_sales_day=views_data.create_dict('sales', 'day', 21),
                graph_deposits_day=graph_deposits_day)


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
                'id':     item.id}
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
            ret['matches'].append(('box', b.name, b.barcode))

        for bv in box_vendors:
            ret['matches'].append(('box', bv.box.name, bv.box.barcode))

        for i in items:
            ret['matches'].append(('item', i.name, i.barcode))

        for iv in item_vendors:
            ret['matches'].append(('item', iv.item.name, iv.item.barcode))

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
    index = 0
    if len(request.GET) != 0:
        for index,packed_values in request.GET.items():
            values = packed_values.split(',')
            line_values = {}
            line_type = values[0]
            line_id = int(values[1])
            line_values['quantity'] = int(values[2])
            line_values['wholesale'] = float(values[3])
            line_values['coupon'] = float(values[4] if values[4] != 'None' else 0)
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

    return {'items': Item.all_force(),
            'boxes': Box.all(),
            'restock_items': restock_items,
            'restock_rows': int(index)+1}


@view_config(route_name='admin_restock_submit',
             request_method='POST',
             permission='manage')
def admin_restock_submit(request):

    # Array of (Item, quantity, total) tuples
    items_for_pricing = []

    # Add an item to the array or update its totals
    def add_item(item, quantity, total):
        for i in range(len(items_for_pricing)):
            if items_for_pricing[i][0].id == item.id:
                items_for_pricing[i][1] += quantity
                items_for_pricing[i][2] += total
                break
        else:
            items_for_pricing.append([item,quantity,total])

    # Arrays to pass to datalayer
    items = []

    for key,val in request.POST.items():

        try:
            f = key.split('-')

            # Only look at the row when we get the id key
            if len(f) >= 2 and f[1] == 'id':

                obj_type   = request.POST['-'.join([f[0], 'type', f[2]])]
                obj_id     = request.POST['-'.join([f[0], 'id', f[2]])]
                quantity   = int(request.POST['-'.join([f[0], 'quantity', f[2]])] or 0)
                wholesale  = float(request.POST['-'.join([f[0], 'wholesale', f[2]])] or Decimal(0.0))
                coupon     = float(request.POST['-'.join([f[0], 'coupon', f[2]])] or Decimal(0.0))
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
                    total *= 1.06
                if btldeposit:
                    total += (0.10 * itemcount * quantity)
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
                    box.wholesale = wholesale
                    box.bottle_dep = btldeposit
                    box.sales_tax = salestax

                    inv_cost = total / (box.subitem_count * quantity)
                    for itembox in box.items:
                        # Set subitem properties too
                        itembox.item.bottle_dep = btldeposit
                        itembox.item.sales_tax = salestax

                        subquantity = itembox.quantity * quantity
                        subtotal    = float(itembox.percentage / 100) * total
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


    # Iterate the grouped items, update prices and wholesales, and then restock
    for item,quantity,total in items_for_pricing:
        if quantity == 0:
            request.session.flash('Error: Attempt to restock item {} with quantity 0. Item skipped.'.format(item), 'error')
            continue
        item.wholesale = Decimal(round(total/quantity, 4))
        # Set the item price
        item.price = round(item.wholesale * Decimal(1.15), 2)

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
        e = datalayer.restock(items, request.user, restock_date)
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


@view_config(route_name='admin_cash_reconcile_submit', request_method='POST',
        permission='manage')
def admin_cash_reconcile_submit(request):
    try:
        if request.POST['amount'].strip() == '':
            # We just got an empty string (and not 0)
            request.session.flash('Error: must enter a cash box amount', 'error')
            return HTTPFound(location=request.route_url('admin_cash_reconcile'))

        amount = Decimal(request.POST['amount'])

        if request.POST['cash-box-reconcile'] == 'on':
            # Make the cashbox total to 0
            expected_amount = datalayer.reconcile_cash(amount, request.user)

            request.session.flash('Cash box recorded successfully', 'success')
            return HTTPFound(location=request.route_url('admin_cash_reconcile_success',
                _query={'amount':amount, 'expected_amount':expected_amount}))
        else:
            # Just move some of the money
            datalayer.cashbox_to_bank(amount, request.user)

            request.session.flash('Moved ${:,.2f} from the cash box to the bank'.format(amount), 'success')
            return HTTPFound(location=request.route_url('admin_index'))

    except decimal.InvalidOperation:
        request.session.flash('Error: Bad value for cash box amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_reconcile'))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error occurred', 'error')
        return HTTPFound(location=request.route_url('admin_cash_reconcile'))


@view_config(route_name='admin_cash_reconcile_success',
        renderer='templates/admin/cash_reconcile_complete.jinja2', permission='manage')
def admin_cash_reconcile_success(request):
    deposit = float(request.GET['amount'])
    expected = float(request.GET['expected_amount'])
    difference = deposit - expected
    return {'cash': {'deposit': deposit,
                     'expected': expected,
                     'difference': difference}}


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
    items = DBSession.query(Item).order_by(Item.name).all()

    undone_inventory = {}
    if len(request.GET) != 0:
        undone_inventory
        for item_id,quantity_counted in request.GET.items():
            undone_inventory[int(item_id)] = int(quantity_counted)

    return {'items': items, 'undone_inventory': undone_inventory}


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
    count = 0
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
                count += 1
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
    if count:
        request.session.flash('{} item{} added successfully.'.format(count, ['s',''][count==1]), 'success')
    else:
        request.session.flash('No items added.', 'error')
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
        return HTTPFound(location=request.route_url('admin_items_edit'))


@view_config(route_name='admin_items_edit',
             renderer='templates/admin/items_edit.jinja2',
             permission='manage')
def admin_items_edit(request):
    items_active = DBSession.query(Item)\
                            .filter_by(enabled=True)\
                            .order_by(Item.name).all()
    items_inactive = DBSession.query(Item)\
                              .filter_by(enabled=False)\
                              .order_by(Item.name).all()
    items = items_active + items_inactive

    # Calculate the number sold here (much faster)
    purchased_items = PurchaseLineItem.all()
    purchased_quantities = {}
    for pi in purchased_items:
        if pi.item_id not in purchased_quantities:
            purchased_quantities[pi.item_id] = 0
        purchased_quantities[pi.item_id] += pi.quantity

    # Calculate the number lost here (much faster)
    lost_items = InventoryLineItem.all()
    lost_quantities = {}
    for li in lost_items:
        if li.item_id not in lost_quantities:
            lost_quantities[li.item_id] = 0
        lost_quantities[li.item_id] += (li.quantity - li.quantity_counted)

    # Get the sale speed
    sale_speeds = views_data.item_sale_speed(30)

    # Get the total amount of inventory we have
    inventory_total = Item.total_inventory_wholesale()

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

    return {'items': items}


@view_config(route_name='admin_items_edit_submit',
             request_method='POST',
             permission='manage')
def admin_items_edit_submit(request):
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
            elif field == 'sales_tax':
                val = request.POST[key] == 'on'
            elif field == 'bottle_dep':
                val = request.POST[key] == 'on'
            else:
                val = request.POST[key].strip()

            setattr(item, field, val)
            DBSession.flush()
        except ValueError:
            # Could not parse price or wholesale as float
            request.session.flash('Error updating {}'.format(name), 'error')
            continue
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
    return HTTPFound(location=request.route_url('admin_items_edit'))


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

        events.extend([e.subtransaction for e in sst])
        events.sort(key=lambda x: x.transaction.event.timestamp)
        events_total += sst_total

        if event_limit is None or events_total <= event_limit:
            events_total = None
        else:
            events = events[:event_limit]

        stats = {}
        stats['stock'] = item.in_stock

        stats['num_sold'] = 0
        purchased_items = PurchaseLineItem.all()
        for pi in purchased_items:
            if pi.item_id == item.id:
                stats['num_sold'] += pi.quantity

        stats['sale_speed'] = views_data.item_sale_speed(30, item.id)

        if stats['sale_speed'] > 0:
            stats['until_out'] = item.in_stock / stats['sale_speed']
        elif item.in_stock <= 0:
            stats['until_out'] = 0
        else:
            stats['until_out'] = '---'

        stats['lost'] = 0
        lost_items = InventoryLineItem.all()
        for li in lost_items:
            if li.item_id == item.id:
                stats['lost'] += (li.quantity - li.quantity_counted)

        inventory_total = Item.total_inventory_wholesale()
        stats['inv_percent'] = ((item.wholesale * item.in_stock) / inventory_total) * 100

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
                    val = round(float(request.POST[key]), 2)
                elif field == 'wholesale':
                    val = round(float(request.POST[key]), 4)
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
        request.session.flash('Error processing item fields.', 'error')
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

                # Set the box percentages all equal
                box_item = BoxItem(box, item, quantity, round((quantity/total_items)*100, 2))
                DBSession.add(box_item)

            if box_itemnum != '':
                # Add a new vendor to the item
                vendor = Vendor.from_id(box_vendor)
                box_vendor = BoxVendor(vendor, box, box_itemnum)
                DBSession.add(box_vendor)

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
            print(box.name)
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
                val = round(float(request.POST[key]), 2)
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
                            boxitem.percentage = round(float(percentage), 2)
                        break
                else:
                    if quantity != '':
                        # Add a new vendor to the item
                        item = Item.from_id(item_id)
                        box_item = BoxItem(box, item, quantity, round(float(percentage), 2))
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
                    val = round(float(request.POST[key]), 2)
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


@view_config(route_name='admin_users_edit',
             renderer='templates/admin/users_edit.jinja2',
             permission='admin')
def admin_users_edit(request):
    enabled_users = DBSession.query(User).filter_by(enabled=True).order_by(User.name).all()
    disabled_users = DBSession.query(User).filter_by(enabled=False).order_by(User.name).all()
    users = enabled_users + disabled_users
    roles = [('user', 'User'),
             ('serviceaccount', 'Service Account'),
             ('manager', 'Manager'),
             ('administrator', 'Administrator')]
    return {'users': users, 'roles': roles}


@view_config(route_name='admin_users_edit_submit',
             request_method='POST',
             permission='admin')
def admin_users_edit_submit(request):
    for key in request.POST:
        user_id = int(key.split('-')[2])
        field = key.split('-')[1]
        val = request.POST[key].strip()

        user = User.from_id(user_id)

        if field == 'role' and user.role == 'user' and val != 'user':
            # The user was previously just a user and now is being set to
            # something else. Every other role type requires a password.
            # Here, we set the password to the default (so the user can
            # login) and the user can change it themselves.
            user.password = request.registry.settings['chezbetty.default_password']

        elif field == 'role' and user.role != 'user' and val == 'user':
            # The user was something other than just a user and is being
            # downgraded. The user no longer needs to be able to login
            # so we reset the password.
            user.password = ''

        setattr(user, field, val)
    request.session.flash('Users updated successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_users_edit'))


@view_config(route_name='admin_user',
             renderer='templates/admin/user.jinja2',
             permission='admin')
def admin_user(request):
    try:
        user = User.from_id(request.matchdict['user_id'])
        my_pools = Pool.all_by_owner(user)
        return {'user': user,
                'my_pools': my_pools}
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Invalid user?', 'error')
        return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_user_balance_edit',
             renderer='templates/admin/user_balance_edit.jinja2',
             permission='admin')
def admin_user_balance_edit(request):
    users = DBSession.query(User).order_by(User.name).all()
    return {'users': users}


@view_config(route_name='admin_user_balance_edit_submit',
             request_method='POST',
             permission='admin')
def admin_user_balance_edit_submit(request):
    try:
        user = User.from_id(int(request.POST['user']))
        adjustment = Decimal(request.POST['amount'])
        reason = request.POST['reason'].strip()
        datalayer.adjust_user_balance(user, adjustment, reason, request.user)
        request.session.flash('User account updated.', 'success')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))
    except NoResultFound:
        request.session.flash('Invalid user?', 'error')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))
    except decimal.InvalidOperation:
        request.session.flash('Invalid adjustment amount.', 'error')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))
    except event.NotesMissingException:
        request.session.flash('Must include a reason', 'error')
        return HTTPFound(location=request.route_url('admin_user_balance_edit'))

def _admin_user_password_reset(user):
    password = user.random_password()
    send_email(TO=user.uniqname+'@umich.edu',
               SUBJECT='Chez Betty Login',
               body=render('templates/admin/email_password.jinja2', {'user': user, 'password': password}))
    return {'status': 'success',
            'msg': 'Password set and emailed to user.'}

@view_config(route_name='admin_user_password_create',
             renderer='json',
             permission='admin')
def admin_user_password_create(request):
    try:
        user = User.from_id(int(request.matchdict['user_id']))
        if user.has_password:
            return {'status': 'error',
                    'msg': 'Error: User already has password.'}
        return _admin_user_password_reset(user)
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
        return _admin_user_password_reset(user)
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
    return {}


@view_config(route_name='admin_users_email_deadbeats',
             request_method='POST',
             permission='admin')
def admin_users_email_deadbeats(request):
    deadbeats = DBSession.query(User).filter(User.enabled).filter(User.balance<-20.0).all()
    for deadbeat in deadbeats:
        send_email(
                TO=deadbeat.uniqname+'@umich.edu',
                SUBJECT='Chez Betty Balance',
                body=render('templates/admin/email_deadbeats.jinja2', {'user': deadbeat})
                )

    request.session.flash('Deadbeat users emailed.', 'success')
    return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_users_email_all',
             request_method='POST',
             permission='admin')
def admin_users_email_all(request):
    users = User.all()
    text = request.POST['text']

    send_email(
            TO='@umich.edu, '.join(users) + '@umich.edu',
            SUBJECT='A message from Chez Betty',
            body=text
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
        return {'pool': pool,
                'pool_owner': User.from_id(pool.owner),
                'users': User.all()}
    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Unable to find pool.', 'error')
        return HTTPFound(location=request.route_url('admin_pools'))


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
        datalayer.add_donation(amount, request.POST['notes'], request.user)

        request.session.flash('Donation recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_index'))

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
    return {}


@view_config(route_name='admin_cash_withdrawal_submit',
             request_method='POST',
             permission='admin')
def admin_cash_withdrawal_submit(request):
    try:
        amount = Decimal(request.POST['amount'])
        datalayer.add_withdrawal(amount, request.POST['notes'], request.user)

        request.session.flash('Withdrawal recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_index'))

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
    btcbox = CashAccount.from_name("btcbox")

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
        btcbox = CashAccount.from_name("btcbox")
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
        expected_usd = Decimal(math.floor(100*((bitcoin_amount*btcbox.balance) / bitcoin_available))/100.0)

        datalayer.reconcile_bitcoins(usd_amount, request.user, expected_amount=expected_usd)
        request.session.flash('Converted %s Bitcoins to %s USD' % (bitcoin_amount, usd_amount), 'success')
    except Exception as e:
        raise e
        #print(e)
        #request.session.flash('Error converting bitcoins', 'error')

    return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_restocks',
             renderer='templates/admin/restocks.jinja2',
             permission='manage')
def admin_restocks(request):
    try:
        LIMIT = int(request.GET['limit'])
        if LIMIT == 0:
            LIMIT = None
    except (KeyError, ValueError):
        LIMIT=50
    events = Event.all(trans_type='restock')
    return {'events': events, 'limit': LIMIT}

@view_config(route_name='admin_events',
             renderer='templates/admin/events.jinja2',
             permission='admin')
def admin_events(request):
    try:
        LIMIT = int(request.GET['limit'])
        if LIMIT == 0:
            LIMIT = None
    except (KeyError, ValueError):
        LIMIT=50
    events = Event.all(limit=LIMIT)
    return {'events': events, 'limit': LIMIT}

@view_config(route_name='admin_events_load_more',
             request_method='POST',
             renderer='json',
             permission='admin')
def admin_events_load_more(request):
    LIMIT=25
    last = int(request.POST['last'])
    events = Event.all(limit=LIMIT,offset=last)

    events_html = []
    for e in events:
        events_html.append(render('templates/admin/events_row.jinja2', {'event': e}))

    return {
            'count': last+LIMIT,
            'rows': events_html
            }

@view_config(route_name='admin_events_deleted',
             renderer='templates/admin/events_deleted.jinja2',
             permission='admin')
def admin_events_deleted(request):
    events_deleted = Event.get_deleted()
    return {'events': events_deleted}


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

        for transaction in event.transactions:
            # Make sure transaction is a deposit (no user check since admin doing)
            if transaction.type not in ('cashdeposit', 'purchase', 'restock', 'inventory'):
                request.session.flash('Error: Only deposits and purchases may be undone.', 'error')
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


@view_config(route_name='admin_shopping_list',
             renderer='templates/admin/shopping.jinja2',
             permission='manage')
def admin_shopping_list(request):
    l = {'misc': []}
    vendors = Vendor.all()
    items = Item.all()
    for item in items:
        if item.in_stock < 10:
            for iv in item.vendors:
                if iv.vendor_id not in l:
                    l[iv.vendor_id] = []
                l[iv.vendor_id].append(item)
            if len(item.vendors) == 0:
                l['misc'].append(item)

    class Object():
        pass

    misc_vendor = Object()
    misc_vendor.name = 'Other'
    misc_vendor.id = 'misc'
    vendors.append(misc_vendor)

    return {'vendors': vendors, 'items': l}


@view_config(route_name='admin_requests',
             renderer='templates/admin/requests.jinja2',
             permission='admin')
def admin_requests(request):
    requests = Request.all()
    return {'requests': requests}


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

@view_config(route_name='login',
             renderer='templates/login.jinja2')
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
    return HTTPFound(location=request.route_url('login'),
                     headers = headers)
