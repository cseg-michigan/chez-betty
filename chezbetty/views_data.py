from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.response import FileResponse
from pyramid.view import view_config, forbidden_view_config

from sqlalchemy.sql import func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import NoResultFound

from .models import *
from .models.model import *
from .models import user as __user
from .models.user import User
from .models.item import Item
from .models.box import Box
from .models.box_item import BoxItem
from .models.transaction import Transaction, Deposit, CashDeposit, BTCDeposit
from .models.transaction import PurchaseLineItem, SubTransaction
from .models.account import Account, VirtualAccount, CashAccount
from .models.event import Event
from .models import event as __event
from .models.vendor import Vendor
from .models.item_vendor import ItemVendor
from .models.request import Request
from .models.announcement import Announcement
from .models.btcdeposit import BtcPendingDeposit
from .models.receipt import Receipt

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
from .btc import Bitcoin, BTCException

# Used for generating barcodes
from reportlab.graphics.barcode import code39
from reportlab.graphics.barcode import code93
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas

from . import utility
import pytz

class InvalidMetric(Exception):
    pass

# fix_timezone
def ftz(i):
    if type(i) is datetime.date:
        i = datetime.datetime(i.year, i.month, i.day)
    return pytz.timezone('America/Detroit').localize(i).astimezone(tz=pytz.timezone('UTC'))


def get_start(days):
    if days:
        # "now" is really midnight tonight, so we really want tomorrows date.
        # This makes the comparisons and math work so 1 day would mean today
        now = datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
        delta = datetime.timedelta(days=days)
        return now - delta
    else:
        # Offset the min by one day so timezone offsets are not an issue
        return datetime.date.min + datetime.timedelta(days=1)

def get_end():
    return datetime.datetime.utcnow().date() + datetime.timedelta(days=1)


def create_x_y_from_group(group, start, end, period, process_output=lambda x: x, default=0):
    x = []
    y = []

    if period == 'year':
        dt = datetime.timedelta(days=365)
        fmt_str = '{}'
    elif period == 'month':
        dt = datetime.timedelta(days=30)
        fmt_str = '{}-{:02}'
    elif period == 'day':
        dt = datetime.timedelta(days=1)
        fmt_str = '{}-{:02}-{:02}'

    # Apparently this is a copy operation
    if start == datetime.date.min:
        ptr = group[0][0]
    else:
        ptr = start

    for d,total in group:
        # Fill in days with no data
        while ptr < datetime.date(d.year, d.month, d.day):
            x.append(fmt_str.format(ptr.year, ptr.month, ptr.day))
            y.append(default)
            ptr += dt

        x.append(fmt_str.format(d.year, d.month, d.day))
        y.append(process_output(total))

        ptr += dt

    # Fill in the end
    while ptr < end:
        x.append(fmt_str.format(ptr.year, ptr.month, ptr.day))
        y.append(default)
        ptr += dt
    return x,y


# Get x,y for some data metric
#
# start:  datetime.datetime that all data must be at or after
# end:    datetime.datetime that all data must be before
# metric: 'items', 'sales', or 'deposits'
# period: 'day', 'month', or 'year'
def admin_data_period_range(start, end, metric, period):
    if metric == 'items':
        data = PurchaseLineItem.quantity_by_period(period, start=ftz(start), end=ftz(end))
        return zip(create_x_y_from_group(data, start, end, period))
    elif metric == 'sales':
        data = PurchaseLineItem.virtual_revenue_by_period(period, start=ftz(start), end=ftz(end))
        return zip(create_x_y_from_group(data, start, end, period, float, 0.0))
    elif metric == 'deposits':
        data = Deposit.deposits_by_period('day', start=ftz(start), end=ftz(end))
        return zip(create_x_y_from_group(data,  start, end, period, float, 0.0))
    elif metric == 'deposits_cash':
        data = CashDeposit.deposits_by_period('day', start=ftz(start), end=ftz(end))
        return zip(create_x_y_from_group(data,  start, end, period, float, 0.0))
    elif metric == 'deposits_btc':
        data = BTCDeposit.deposits_by_period('day', start=ftz(start), end=ftz(end))
        return zip(create_x_y_from_group(data,  start, end, period, float, 0.0))
    else:
        raise(InvalidMetric(metric))


def admin_data_period(num_days, metric, period):
    return admin_data_period_range(get_start(num_days), get_end(), metric, period)


###
### "Each" functions. So "monday", "tuesday", etc. instead of 2014-07-21
###

month_each_mapping = [(i, datetime.date(2000,i,1).strftime('%B')) for i in range(1,13)]

day_each_mapping = [(i, '{:02}'.format(i)) for i in range(0,31)]

weekday_each_mapping = [(6, 'Sunday'), (0, 'Monday'), (1, 'Tuesday'),
                        (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'),
                        (5, 'Saturday')]

hour_each_mapping = [(i, '{0:02}:00-{0:02}:59'.format(i)) for i in range(0,24)]


def create_x_y_from_group_each(group, mapping, start, end, process_output=lambda x: x, default=0):
    x = []
    y = []

    for d in mapping:
        # Put the x axis label in the x array
        x.append(d[1])

        if d[0] in group:
            # We have a reading for this particular time unit
            y.append(process_output(group[d[0]]))
        else:
            y.append(default)

    return x,y


# Get data about each something. So each weekday, or each hour
#
# metric: 'items', 'sales', or 'deposits'
# each:   'day_each' or 'hour_each'
def admin_data_each_range(start, end, metric, each):
    if each == 'month_each':
        mapping = month_each_mapping
    elif each == 'day_each':
        mapping = day_each_mapping
    elif each == 'weekday_each':
        mapping = weekday_each_mapping
    elif each == 'hour_each':
        mapping = hour_each_mapping

    if metric == 'items':
        data = PurchaseLineItem.quantity_by_period(each, start=ftz(start), end=ftz(end))
        return zip(create_x_y_from_group_each(data, mapping, start, end))
    elif metric == 'sales':
        data = PurchaseLineItem.virtual_revenue_by_period(each, start=ftz(start), end=ftz(end))
        return zip(create_x_y_from_group_each(data, mapping, start, end, float, 0.0))
    elif metric == 'deposits':
        data = Deposit.deposits_by_period(each, start=ftz(start), end=ftz(end))
        return zip(create_x_y_from_group_each(data, mapping, start, end, float, 0.0))
    else:
        raise(InvalidMetric(metric))


def admin_data_each(num_days, metric, each):
    return admin_data_each_range(get_start(num_days), get_end(), metric, each)



def create_json(request, metric, period):
    try:
        if 'days' in request.GET:
            num_days = int(request.GET['days'])
        else:
            num_days = 0
        if 'each' in period:
            x,y = admin_data_each(num_days, metric, period)
        else:
            x,y = admin_data_period(num_days, metric, period)
        return {'x': x,
                'y': y,
                'num_days': num_days or 'all'}
    except ValueError:
        return {'status': 'error'}
    except utility.InvalidGroupPeriod as e:
        return {'status': 'error',
                'message': 'Invalid period for grouping data: {}'.format(e)}
    except InvalidMetric as e:
        return {'status': 'error',
                'message': 'Invalid metric for requesting data: {}'.format(e)}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error'}


def create_dict_to_date(metric, period):
    now = datetime.date.today()

    if period == 'month':
        start = datetime.date(now.year, now.month, 1)
    elif period == 'year':
        start = datetime.date(now.year, 1, 1)

    xs,ys = admin_data_period_range(start, get_end(), metric, period)

    return {'xs': xs,
            'ys': ys}


def create_dict(metric, period, num_days):
    if 'each' in period:
        xs,ys = admin_data_each(num_days, metric, period)
    else:
        xs,ys = admin_data_period(num_days, metric, period)

    return {'xs': xs,
            'ys': ys,
            'avg': [sum(y)/len(y) for y in ys],
            'avg_hack': [[sum(y)/len(y)]*len(y) for y in ys],
            'num_days': num_days or 'all'}


# Get a list of timestamps and the number of a particular item that was sold
# at that time.
def create_item_sales_json(request, item_id):
    sales = PurchaseLineItem.item_sale_quantities(item_id)

    individual = []
    totals = []
    total = 0
    for s in sales:
        tstamp = round(s[1].timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
        individual.append((tstamp, s[0].quantity))
        total += s[0].quantity
        totals.append((tstamp, total))

    return {'individual': individual,
            'sum': totals}

#######
### Calculate the speed of sale for all items

# We are going to do this over all time and over the last 30 days

# Returns a dict of {item_num -> {number of days -> sale speed}}
def item_sale_speed(num_days, only_item_id=None):
    # TODO: If we're only looking for one item (only_item_id), this can probably
    # be made more efficient

    # First we need to figure out when each item was in stock and when it wasn't.
    # I don't know what the best way to do this is. I think the easiest way is
    # to look at the in_stock column in the item_history table and figure it
    # out from there.

    # Start by getting all item change events for the last thirty days
    data = {}

    data_onsale = {}

    start = get_start(num_days)
    start_datetime = datetime.datetime(start.year, start.month, start.day)

    start_padding = get_start(num_days*3)
    start_str = start_padding.strftime('%Y-%m-%d 0:0')
    items = DBSession.execute("SELECT * FROM items_history\
                               WHERE item_changed_at>'{}'\
                               ORDER BY item_changed_at ASC".format(start_str))

    # Calculate the number of days in the interval the item was in stock
    for item in items:
        status = item.in_stock>0

        if item.id not in data_onsale:
            data_onsale[item.id] = {'days_on_sale': 0, 
                                    'date_in_stock': None,
                                    'num_sold': 0}

        if item.item_changed_at < start_datetime:
            # We need to figure out if the item started in stock at the
            # beginning of the time period.
            if status == True:
                data_onsale[item.id]['date_in_stock'] = start_datetime
            else:
                data_onsale[item.id]['date_in_stock'] = None

        elif (status == True) and (data_onsale[item.id]['date_in_stock'] == None):
            # item is in stock now and wasn't before
            data_onsale[item.id]['date_in_stock'] = item.item_changed_at

        elif (status == False) and (data_onsale[item.id]['date_in_stock'] != None):
            # Item is now out of stock

            # calculate time difference
            tdelta = item.item_changed_at - data_onsale[item.id]['date_in_stock']
            data_onsale[item.id]['days_on_sale'] += tdelta.days
            #print('{}: {}'.format(item.id, tdelta))

            data_onsale[item.id]['date_in_stock'] = None

    for item_id,item_data in data_onsale.items():
        if item_data['date_in_stock'] != None:
            tdelta = datetime.datetime.now() - item_data['date_in_stock']
            item_data['days_on_sale'] += tdelta.days
            #print('{}: {}'.format(item_id, tdelta.days))


    # Calculate the number of items sold during the period
    purchases = DBSession.query(PurchaseLineItem)\
                         .join(Transaction)\
                         .join(Event)\
                         .filter(Event.deleted==False)\
                         .filter(Event.timestamp>start)
    for purchase in purchases:
        item_id = purchase.item_id
        quantity = purchase.quantity
        data_onsale[item_id]['num_sold'] += quantity


    # Calculate rate, finally
    for itemid,item_data in data_onsale.items():
        if item_data['days_on_sale'] == 0:
            data[itemid] = 0
            continue
        data[itemid] = item_data['num_sold'] / item_data['days_on_sale']

    if only_item_id:
        return data[only_item_id]
    else:
        return data




@view_config(route_name='admin_data_items_json',
             renderer='json',
             permission='manage')
def admin_data_items_json(request):
    return create_json(request, 'items', request.matchdict['period'])


@view_config(route_name='admin_data_sales_json',
             renderer='json',
             permission='manage')
def admin_data_sales_json(request):
    return create_json(request, 'sales', request.matchdict['period'])


@view_config(route_name='admin_data_deposits_json',
             renderer='json',
             permission='manage')
def admin_data_deposits_json(request):
    return create_json(request, 'deposits', request.matchdict['period'])


@view_config(route_name='admin_data_items_each_json',
             renderer='json',
             permission='manage')
def admin_data_items_each_json(request):
    return create_json(request, 'items', request.matchdict['period']+'_each')


@view_config(route_name='admin_data_sales_each_json',
             renderer='json',
             permission='manage')
def admin_data_sales_each_json(request):
    return create_json(request, 'sales', request.matchdict['period']+'_each')


@view_config(route_name='admin_data_deposits_each_json',
             renderer='json',
             permission='manage')
def admin_data_deposits_each_json(request):
    return create_json(request, 'deposits', request.matchdict['period']+'_each')


# All of the sale dates and quantities of a particular item
@view_config(route_name='admin_data_item_sales_json',
             renderer='json',
             permission='manage')
def admin_data_item_sales_json(request):
    return create_item_sales_json(request, request.matchdict['item_id'])


# Timestamps and the number of total users
@view_config(route_name='admin_data_users_totals_json',
             renderer='json',
             permission='manage')
def admin_data_users_totals_json(request):
    return User.get_user_count_cumulative()




@view_config(route_name='admin_data_speed_items',
             renderer='json',
             permission='manage')
def admin_data_speed_items(request):
    return item_sale_speed(30)

