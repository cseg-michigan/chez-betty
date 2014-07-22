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
from .models.transaction import Transaction, Deposit, BTCDeposit
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


def get_start(days):
    if days:
        # "now" is really midnight tonight, so we really want tomorrows date.
        # This makes the comparisons and math work so 1 day would mean today
        now = datetime.date.today() + datetime.timedelta(days=1)
        delta = datetime.timedelta(days=days)
        return now - delta
    else:
        return datetime.date.min

def get_end():
    return datetime.date.today() + datetime.timedelta(days=1)


def create_x_y_from_group(group, start, end, process_output=None, default=0):
    x = []
    y = []

    # Apparently this is a copy operation
    if start == datetime.date.min:
        day_ptr = group[0]['day']
    else:
        day_ptr = start

    for g in group:
        # Fill in days with no data
        while day_ptr < datetime.date(g['day'].year, g['day'].month, g['day'].day):
            x.append('{}-{}-{}'.format(day_ptr.year, day_ptr.month, day_ptr.day))
            y.append(default)
            day_ptr += datetime.timedelta(days=1)

        x.append('{}-{}-{}'.format(g['day'].year, g['day'].month, g['day'].day))
        if process_output:
            t = process_output(g['total'])
        else:
            t = g['total']
        y.append(t)

        day_ptr += datetime.timedelta(days=1)

    # Fill in the end
    while day_ptr < end:
        x.append('{}-{}-{}'.format(day_ptr.year, day_ptr.month, day_ptr.day))
        y.append(default)
        day_ptr += datetime.timedelta(days=1)
    return x,y


def admin_data_items_day_range(start, end):
    sold_day = PurchaseLineItem.quantity_by_period('day', start=start, end=end)
    return create_x_y_from_group(sold_day, start, end)

def admin_data_items_day(num_days):
    return admin_data_items_day_range(get_start(num_days), get_end())


def admin_data_sales_day_range(start, end):
    sold_day = PurchaseLineItem.virtual_revenue_by_period('day', start=start, end=end)
    return create_x_y_from_group(sold_day, start, end, float, 0.0)

def admin_data_sales_day(num_days):
    return admin_data_sales_day_range(get_start(num_days), get_end())


def admin_data_deposits_day_range(start, end):
    dep_day = Deposit.deposits_by_period('day', start=start, end=end)
    return create_x_y_from_group(dep_day, start, end, float, 0.0)

def admin_data_deposits_day(num_days):
    return admin_data_deposits_day_range(get_start(num_days), get_end())



###
### "Each" functions. So "monday", "tuesday", etc. instead of 2014-07-21
###

day_each_mapping = [(6, 'Sunday'), (0, 'Monday'), (1, 'Tuesday'),
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


def admin_data_items_day_each_range(start, end):
    sold_day = PurchaseLineItem.quantity_by_period('day_each', start=start, end=end)
    return create_x_y_from_group_each(sold_day, day_each_mapping, start, end)

def admin_data_items_day_each(num_days):
    return admin_data_items_day_each_range(get_start(num_days), get_end())


def admin_data_items_hour_each_range(start, end):
    sold_day = PurchaseLineItem.quantity_by_period('hour_each', start=start, end=end)
    return create_x_y_from_group_each(sold_day, hour_each_mapping, start, end)

def admin_data_items_hour_each(num_days):
    return admin_data_items_hour_each_range(get_start(num_days), get_end())



def create_json(request, axes_func, desc):
    try:
        if 'days' in request.GET:
            num_days = int(request.GET['days'])
        else:
            num_days = 0
        x,y = axes_func(num_days)
        return {'x': x,
                'y': y,
                'num_days': num_days or 'all',
                'desc': desc}
    except ValueError:
        return {'status': 'error'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error'}


def create_dict(axes_func, num_days):
    x,y = axes_func(num_days)
    return {'x': x,
            'y': y,
            'num_days': num_days or 'all'}




@view_config(route_name='admin_data_items_day_json',
             renderer='json',
             permission='manage')
def admin_data_items_day_json(request):
    return create_json(request, admin_data_items_day, 'Items sold per day')


@view_config(route_name='admin_data_sales_day_json',
             renderer='json',
             permission='manage')
def admin_data_sales_day_json(request):
    return create_json(request, admin_data_sales_day, 'Sales per day')


@view_config(route_name='admin_data_deposits_day_json',
             renderer='json',
             permission='manage')
def admin_data_deposits_day_json(request):
    return create_json(request, admin_data_deposits_day, 'Deposits per day')





@view_config(route_name='admin_data_items_day_each_json',
             renderer='json',
             permission='manage')
def admin_data_items_day_each_json(request):
    return create_json(request, admin_data_items_day_each, 'Items sold on each day')

@view_config(route_name='admin_data_items_hour_each_json',
             renderer='json',
             permission='manage')
def admin_data_items_hour_each_json(request):
    return create_json(request, admin_data_items_hour_each, 'Items sold in each hour')

