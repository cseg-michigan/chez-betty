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
    # "now" is really midnight tonight, so we really want tomorrows date.
    # This makes the comparisons and math work so 1 day would mean today
    now = datetime.datetime.now() + datetime.timedelta(days=1)
    delta = datetime.timedelta(days=days)
    return now - delta

def get_end():
    return datetime.datetime.now() + datetime.timedelta(days=1)


def create_x_y_from_group (group, start, end, process_output=None, default=0):
    x = []
    y = []

    # Apparently this is a copy operation
    day_ptr = start

    for g in group:
        # Fill in days with no data
        while day_ptr < datetime.datetime(g['day'].year, g['day'].month, g['day'].day):
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



@view_config(route_name='admin_data_items_day_json',
             renderer='json',
             permission='manage')
def admin_data_items_day_json(request):
    try:
        if 'days' in request.GET:
            num_days = int(request.GET['days'])
        else:
            num_days = 30
        x,y = admin_data_items_day(num_days)
        return {'x': x,
                'y': y,
                'num_days': num_days,
                'desc': 'Items sold per day'}
    except ValueError:
        return {'status': 'error'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error'}


@view_config(route_name='admin_data_sales_day_json',
             renderer='json',
             permission='manage')
def admin_data_sales_day_json(request):
    try:
        if 'days' in request.GET:
            num_days = int(request.GET['days'])
        else:
            num_days = 30
        x,y = admin_data_sales_day(num_days)
        return {'x': x,
                'y': y,
                'num_days': num_days,
                'desc': 'Sales per day'}
    except ValueError:
        return {'status': 'error'}
    except Exception as e:
        if request.debug: raise(e)
        return {'status': 'error'}
