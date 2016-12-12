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
import arrow

class InvalidMetric(Exception):
    pass

# fix_timezone
def ftz(i):
    return i
    #if type(i) is datetime.date:
    #    i = datetime.datetime(i.year, i.month, i.day)
    #return pytz.timezone('America/Detroit').localize(i).astimezone(tz=pytz.timezone('UTC'))


def get_start(days):
    if days:
        # "now" is really midnight tonight, so we really want tomorrows date.
        # This makes the comparisons and math work so 1 day would mean today
        now = arrow.utcnow() + datetime.timedelta(days=1)
        delta = datetime.timedelta(days=days)
        return now - delta
    else:
        # Hard code in when Betty started
        return arrow.get(datetime.date(year=2014, month=7, day=8))

def get_end():
    return arrow.utcnow() + datetime.timedelta(days=1)


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
        while ptr < arrow.get(datetime.date(d.year, d.month, d.day)):
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

def datetime_to_timestamps (data, process_output=lambda x: x):
    out = []
    for d in data:
        t = arrow.get(
                datetime.datetime(
                    year=d[0].year,
                    month=d[0].month,
                    day=d[0].day,
                    hour=12,
                    )
                ).timestamp * 1000
        #t = round(datetime.datetime(year=d[0].year, month=d[0].month, day=d[0].day, hour=12)\
        #          .replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
        # t = round(datetime.datetime.combine(d[0], datetime.datetime.min.time())\
        #           .replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
        out.append((t, process_output(d[1])))
    return out


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

def admin_data_highcharts_period(metric, period):
    start = get_start(0)
    end = get_end()
    if metric == 'items':
        data = PurchaseLineItem.quantity_by_period(period, start=ftz(start), end=ftz(end))
        return datetime_to_timestamps(data)
    elif metric == 'sales':
        data = PurchaseLineItem.virtual_revenue_by_period(period, start=ftz(start), end=ftz(end))
        return datetime_to_timestamps(data, float)
    elif metric == 'deposits':
        data = Deposit.deposits_by_period('day', start=ftz(start), end=ftz(end))
        return datetime_to_timestamps(data, float)
    elif metric == 'deposits_cash':
        data = CashDeposit.deposits_by_period('day', start=ftz(start), end=ftz(end))
        return datetime_to_timestamps(data, float)
    elif metric == 'deposits_btc':
        data = BTCDeposit.deposits_by_period('day', start=ftz(start), end=ftz(end))
        return datetime_to_timestamps(data, float)
    else:
        raise(InvalidMetric(metric))


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


def create_highcharts_json(request, metric, period):
    try:
        return admin_data_highcharts_period(metric, period)
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
        start = arrow.get(datetime.date(now.year, now.month, 1))
    elif period == 'year':
        start = arrow.get(datetime.date(now.year, 1, 1))

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
        tstamp = s[1].timestamp.timestamp*1000
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
    start_datetime = arrow.get(datetime.datetime(start.year, start.month, start.day))

    start_padding = get_start(num_days*3)
    start_str = start_padding.strftime('%Y-%m-%d 0:0')
    # This gets a little hairy b/c we circumvent sqlalchemy here. This means
    # that timestamps aren't automatically converted into arrow objects, so we
    # have to do it ourselves everywhere we access them
    items = DBSession.execute("SELECT * FROM items_history\
                               WHERE item_changed_at>'{}'\
                               ORDER BY item_changed_at ASC".format(start_str))

    # Calculate the number of days in the interval the item was in stock
    for item in items:
        status = item.in_stock>0

        item_changed_at = arrow.get(item.item_changed_at)

        if item.id not in data_onsale:
            data_onsale[item.id] = {'days_on_sale': 0,
                                    'date_in_stock': None,
                                    'num_sold': 0}

        if item_changed_at < start_datetime:
            # We need to figure out if the item started in stock at the
            # beginning of the time period.
            if status == True:
                data_onsale[item.id]['date_in_stock'] = start_datetime
            else:
                data_onsale[item.id]['date_in_stock'] = None

        elif (status == True) and (data_onsale[item.id]['date_in_stock'] == None):
            # item is in stock now and wasn't before
            data_onsale[item.id]['date_in_stock'] = item_changed_at

        elif (status == False) and (data_onsale[item.id]['date_in_stock'] != None):
            # Item is now out of stock

            # calculate time difference
            tdelta = item_changed_at - data_onsale[item.id]['date_in_stock']
            data_onsale[item.id]['days_on_sale'] += tdelta.days
            #print('{}: {}'.format(item.id, tdelta))

            data_onsale[item.id]['date_in_stock'] = None

    for item_id,item_data in data_onsale.items():
        if item_data['date_in_stock'] != None:
            tdelta = arrow.now() - item_data['date_in_stock']
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

        # Not sure this check should be necessary, but just make sure
        if item_id not in data_onsale:
            data_onsale[item_id] = {'days_on_sale': 0,
                                    'date_in_stock': None,
                                    'num_sold': 0}

        data_onsale[item_id]['num_sold'] += quantity


    # Calculate rate, finally
    for itemid,item_data in data_onsale.items():
        if item_data['days_on_sale'] == 0:
            data[itemid] = 0
            continue
        data[itemid] = item_data['num_sold'] / item_data['days_on_sale']

    if only_item_id:
        if only_item_id in data:
            return data[only_item_id]
        else:
            return 0
    else:
        return data


#######
### Calculate a histogram of user balances
#
# This has a special feature where it counts 0.00 as its own special bin
def user_balance_histogram ():
    bin_size = 5 # $5
    bins = {}

    def to_bin (x):
        if x == Decimal(0):
            return 0
        start = int(bin_size * round(float(x)/bin_size))
        if start == 0:
            start = 0.01
        return start

    users = User.get_normal_users()
    for user in users:
        balance_bin = to_bin(user.balance)
        if balance_bin not in bins:
            bins[balance_bin] = 1
        else:
            bins[balance_bin] += 1

    out = {}

    out['raw'] = bins

    last = None
    x = []
    y = []
    for bin_start, count in sorted(bins.items()):
        zero = False

        # Handle near 0 special
        if bin_start == 0:
            zero = True

        if bin_start == 0.01:
            bin_start = 0

        # Fill in missing bins, if needed
        if last != None and bin_start-last > bin_size:
            for i in range(last+bin_size, bin_start, bin_size):
                b = '{} to {}'.format(i, i+bin_size)
                x.append(b)
                y.append(0)

        if zero:
            b = '0'
        else:
            b = '{} to {}'.format(bin_start, bin_start+bin_size)
        x.append(b)
        y.append(count)

        last = bin_start

    out['x'] = x
    out['y'] = y

    return out


#######
### Calculate a histogram of user days since last purchase
#
# This has a special feature where it counts 0.00 as its own special bin
def user_dayssincepurchase_histogram ():
    bin_size = 10 # days
    bins = {}

    def to_bin (x):
        if x == None:
            return None
        return int(bin_size * round(float(x)/bin_size))

    users = User.get_normal_users()
    for user in users:
        the_bin = to_bin(user.days_since_last_purchase)
        if the_bin != None:
            if the_bin not in bins:
                bins[the_bin] = 1
            else:
                bins[the_bin] += 1

    out = {}

    out['raw'] = bins

    last = None
    x = []
    y = []
    for bin_start, count in sorted(bins.items()):
        # Fill in missing bins, if needed
        if last != None and bin_start-last > bin_size:
            for i in range(last+bin_size, bin_start, bin_size):
                b = '{} to {}'.format(i, i+bin_size)
                x.append(b)
                y.append(0)

        b = '{} to {}'.format(bin_start, bin_start+bin_size)
        x.append(b)
        y.append(count)

        last = bin_start

    out['x'] = x
    out['y'] = y

    return out


#######
### Calculate a histogram of number of purchases by each user
#
#
def user_numberofpurchases_histogram ():
    bins = {}

    users = User.get_normal_users()
    for user in users:
        number_purchases = user.number_of_purchases
        if number_purchases > 200:
            number_purchases = 200

        if number_purchases not in bins:
            bins[number_purchases] = 1
        else:
            bins[number_purchases] += 1

    out = {}

    last = None
    x = []
    y = []
    for bin_start, count in sorted(bins.items()):
        # Fill in missing bins, if needed
        if last != None and bin_start-last > 1:
            for i in range(last, bin_start):
                b = '{}'.format(i)
                x.append(b)
                y.append(0)

        b = '{}'.format(bin_start)
        x.append(b)
        y.append(count)

        last = bin_start

    out['x'] = x
    out['y'] = y

    return out


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


@view_config(route_name='admin_data_json_highcharts',
             renderer='json',
             permission='manage')
def admin_data_json_highcharts(request):
    return create_highcharts_json(request, request.matchdict['metric'], request.matchdict['period'])


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


# Timestamps and user debt, bank balance, debt/# users in debt
@view_config(route_name='admin_data_users_balance_totals_json',
             renderer='json',
             permission='manage')
def admin_data_users_balance_totals_json(request):
    return Transaction.get_balance_total_daily()


# Timestamps and balance for a specific user over time
@view_config(route_name='admin_data_user_balance_json',
             renderer='json',
             permission='manage')
def admin_data_user_balance_json(request):
    user = User.from_id(request.matchdict['user_id'])
    return Transaction.get_balances_over_time_for_user(user)


# # Timestamps and user debt, "bank balance", debt/user
# @view_config(route_name='admin_data_users_balance_totals_percapita_json',
#              renderer='json',
#              permission='manage')
# def admin_data_users_balance_totals_percapita_json(request):
#     debt = Transaction.get_balance_total_daily()
#     users = User.get_user_count_cumulative()

#     di = 0
#     ui = 0
#     next_user_time = users[ui][0]
#     user_count = users[ui][1]
#     out = []

#     for rec in debt:
#         timestamp = rec[0]
#         debt = rec[1]
#         balance = rec[2]

#         # Look for the correct number of users
#         while timestamp > next_user_time:
#             ui += 1
#             if ui >= len(users):
#                 break
#             next_user_time = users[ui][0]
#             user_count = users[ui][1]

#         debt_per_capita = debt/user_count

#         out.append((timestamp, debt, balance, debt_per_capita))

#     return out


@view_config(route_name='admin_data_speed_items',
             renderer='json',
             permission='manage')
def admin_data_speed_items(request):
    return item_sale_speed(30)


@view_config(route_name='admin_data_histogram_balances',
             renderer='json',
             permission='manage')
def admin_data_histogram_balances(request):
    return user_balance_histogram()


@view_config(route_name='admin_data_histogram_dayssincepurchase',
             renderer='json',
             permission='manage')
def admin_data_histogram_dayssincepurchase(request):
    return user_dayssincepurchase_histogram()


@view_config(route_name='admin_data_histogram_numberofpurchases',
             renderer='json',
             permission='manage')
def admin_data_histogram_numberofpurchases(request):
    return user_numberofpurchases_histogram()

