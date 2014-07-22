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
from .models.transaction import Transaction, Deposit, BTCDeposit, PurchaseLineItem, SubTransaction
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

import uuid
import twitter


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
        count['requests']     = Request.count()
        event.rendering_val['counts'] = count


###
### Admin
###

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
    users_balance   = DBSession.query(func.sum(User.balance).label("total_balance")).one()
    bsi             = DBSession.query(func.sum(PurchaseLineItem.quantity).label('quantity'), Item.name, Item.id)\
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

    try:
        btc_balance = Bitcoin.get_balance()
        btc = {"btc": btc_balance,
               "mbtc": round(btc_balance*1000, 2),
               "usd": btc_balance * Bitcoin.get_spot_price()}
    except BTCException:
        btc = {"btc": None,
               "mbtc": None,
               "usd": None}

    sold_by_day         = PurchaseLineItem.quantity_by_period('day')
    virt_revenue_by_day = PurchaseLineItem.virtual_revenue_by_period('day')
    deposits_by_day     = Deposit.deposits_by_period('day')

    return dict(events=events,
                items_low_stock=items_low_stock,
                users_shame=users_shame,
                users_balance=users_balance,
                cashbox=cashbox,
                btcbox=btcbox,
                chezbetty_cash=chezbetty_cash,
                chezbetty=chezbetty,
                btc_balance=btc,
                cashbox_net=cashbox_net,
                btcbox_net=btcbox_net,
                chezbetty_net=chezbetty_net,
                restock=restock,
                donation=donation,
                withdrawal=withdrawal,
                inventory=inventory,
                best_selling_items=bsi,
                sold_by_day=sold_by_day,
                virt_revenue_by_day=virt_revenue_by_day,
                deposits_by_day=deposits_by_day, 
                graph_items_day=views_data.create_dict('items', 'day', 30),
                graph_sales_day=views_data.create_dict('sales', 'day', 30),
                graph_deposits_day=views_data.create_dict('deposits', 'day', 30))


@view_config(route_name='admin_demo',
             permission='admin')
def admin_demo(request):
    if request.matchdict['state'].lower() == 'true':
        request.response.set_cookie('demo', '1')
    else:
        request.response.set_cookie('demo', '0')
    return request.response


@view_config(route_name='admin_keyboard',
             permission='manage')
def admin_keyboard(request):
    if request.matchdict['state'].lower() == 'true':
        request.response.set_cookie('keyboard', '1')
    else:
        request.response.set_cookie('keyboard', '0')
    return request.response


@view_config(route_name='admin_item_barcode_json',
             renderer='json',
             permission='manage')
def admin_item_barcode_json(request):
    try:
        item = Item.from_barcode(request.matchdict['barcode'])
        html = render('templates/admin/restock_row.jinja2', {'item': item})
        return {'status': 'success',
                'type':   'item',
                'data':   html,
                'id':     item.id}
    except NoResultFound:
        try:
            box = Box.from_barcode(request.matchdict['barcode'])
            html = render('templates/admin/restock_row.jinja2', {'box': box})
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


@view_config(route_name='admin_restock',
             renderer='templates/admin/restock.jinja2',
             permission='manage')
def admin_restock(request):
    return {'items': Item.all(), 'boxes': Box.all()}


@view_config(route_name='admin_restock_submit',
             request_method='POST',
             permission='manage')
def admin_restock_submit(request):
    i = iter(request.POST)

    # Array of (Item, quantity, total) tuples
    items = []

    # Add an item to the array or update its totals
    def add_item(item, quantity, total):
        for i in range(len(items)):
            if items[i][0].id == item.id:
                items[i][1] += quantity
                items[i][2] += total
                break
        else:
            items.append([item,quantity,total])

    for salestax,quantity,cost,total in zip(i,i,i,i):
        if not (quantity.split('-')[3] == cost.split('-')[3] == salestax.split('-')[3]):
            request.session.flash('Error: Malformed POST. Misaligned IDs.', 'error')
            DBSession.rollback()
            return HTTPFound(location=request.route_url('admin_restock'))

        try:
            fields = quantity.split('-')
            obj_type = fields[1]
            obj_id   = int(fields[3])
            quantity = int(request.POST[quantity])
            total    = Decimal(request.POST[total])

            if request.POST[salestax] == 'on':
                total = (total * Decimal(1.06))

            if obj_type == 'item':
                item = Item.from_id(obj_id)
                add_item(item, quantity, total)
            elif obj_type == 'box':
                box = Box.from_id(obj_id)
                # Boxes should have a wholesale that can actually be purchased
                box.wholesale = Decimal(round(total, 2))

                # Cost for any one item
                inv_cost = box.wholesale / box.subitem_count

                # Add all the items in the box and figure out their wholesales
                for itembox in box.items:
                    subquantity = itembox.quantity * quantity
                    subtotal    = (itembox.quantity * quantity) * inv_cost
                    add_item(itembox.item, subquantity, subtotal)

            else:
                request.session.flash('Invalid item type', 'error')
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
            request.session.flash('Error restocking item. Skipped.', 'error')
            continue

    # Iterate the grouped items, update prices and wholesales, and then restock
    restock_items = {}
    for item,quantity,total in items:
        item.wholesale = Decimal(round(total/quantity, 4))
        # Make sure we aren't selling at a loss cause that would be dumb
        if item.price < item.wholesale:
            item.price = round(item.wholesale * Decimal(1.15), 2)
        restock_items[item] = quantity

    datalayer.restock(restock_items, request.user)
    request.session.flash('Restock complete.', 'success')
    return HTTPFound(location=request.route_url('admin_items_edit'))


@view_config(route_name='admin_cash_reconcile',
             renderer='templates/admin/cash_reconcile.jinja2',
             permission='manage')
def admin_cash_reconcile(request):
    return {}


@view_config(route_name='admin_cash_reconcile_submit', request_method='POST',
        permission='manage')
def admin_cash_reconcile_submit(request):
    try:
        if request.POST['amount'] == '':
            # We just got an empty string (and not 0)
            request.session.flash('Error: must enter a cash box amount', 'error')
            return HTTPFound(location=request.route_url('admin_cash_reconcile'))

        amount = Decimal(request.POST['amount'])
        expected_amount = datalayer.reconcile_cash(amount, request.user)

        request.session.flash('Cash box recorded successfully', 'success')
        return HTTPFound(location=request.route_url('admin_cash_reconcile_success',
            _query={'amount':amount, 'expected_amount':expected_amount}))

    except decimal.InvalidOperation:
        request.session.flash('Error: Bad value for cash box amount', 'error')
        return HTTPFound(location=request.route_url('admin_cash_reconcile'))


@view_config(route_name='admin_cash_reconcile_success',
        renderer='templates/admin/cash_reconcile_complete.jinja2', permission='manage')
def admin_cash_reconcile_success(request):
    deposit = float(request.GET['amount'])
    expected = float(request.GET['expected_amount'])
    difference = deposit - expected
    return {'cash': {'deposit': deposit, 'expected': expected, 'difference': difference}}


@view_config(route_name='admin_inventory',
             renderer='templates/admin/inventory.jinja2',
             permission='manage')
def admin_inventory(request):
    items = DBSession.query(Item).order_by(Item.name).all()
    return {'items': items}


@view_config(route_name='admin_inventory_submit',
             request_method='POST',
             permission='manage')
def admin_inventory_submit(request):
    items = {}
    for key in request.POST:
        item = Item.from_id(key.split('-')[2])
        try:
            items[item] = int(request.POST[key])
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


@view_config(route_name='admin_items_add',
             renderer='templates/admin/items_add.jinja2',
             permission='manage')
def admin_items_add(request):
    if len(request.GET) == 0:
        return {'items': {'count': 1,
                          'name-0': '',
                          'barcode-0': '',
                         }}
    else:
        return {'items': request.GET}


@view_config(route_name='admin_items_add_submit',
             request_method='POST',
             permission='manage')
def admin_items_add_submit(request):
    count = 0
    error_items = []

    # Iterate all the POST keys and find the ones that are item names
    for key in request.POST:
        if 'item-name-' in key:
            id = int(key.split('-')[2])
            stock = 0
            wholesale = 0
            price = 0
            enabled = False

            # Parse out the important fields looking for errors
            try:
                name = request.POST['item-name-{}'.format(id)]
                barcode = request.POST['item-barcode-{}'.format(id)]

                # Check that name and barcode are not blank. If name is blank
                # treat this as an empty row and skip. If barcode is blank
                # we will get a database error so send that back to the user.
                if name == '':
                    continue
                if barcode == '':
                    request.session.flash('Error adding item "{}". Barcode cannot be blank.'.format(name), 'error')
                    error_items.append({
                        'name': name, 'barcode': ''
                    })
                    continue

                # Add the item to the DB
                item = Item(name, barcode, price, wholesale, stock, enabled)
                DBSession.add(item)
                DBSession.flush()
                count += 1
            except:
                if len(name):
                    error_items.append({
                            'name' : request.POST['item-name-{}'.format(id)],
                            'barcode' : request.POST['item-barcode-{}'.format(id)]
                            })
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
                flat['{}-{}'.format(k, e_count)] = v
            e_count += 1
        flat['count'] = len(error_items)
        return HTTPFound(location=request.route_url('admin_items_add', _query=flat))
    else:
        return HTTPFound(location=request.route_url('admin_items_edit'))


@view_config(route_name='admin_items_edit',
             renderer='templates/admin/items_edit.jinja2',
             permission='manage')
def admin_items_edit(request):
    items_active = DBSession.query(Item).filter_by(enabled=True).order_by(Item.name).all()
    items_inactive = DBSession.query(Item).filter_by(enabled=False).order_by(Item.name).all()
    items = items_active + items_inactive
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
            else:
                val = request.POST[key]

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
        item = Item.from_id(request.matchdict['item_id'])
        vendors = Vendor.all()
        subtransactions = SubTransaction.all_item(item.id)

        # Don't display vendors that already have an item number in the add
        # new vendor item number section
        used_vendors = []
        for vendoritem in item.vendors:
            if vendoritem.enabled:
                used_vendors.append(vendoritem.vendor_id)
        new_vendors = []
        for vendor in vendors:
            if vendor.id not in used_vendors and vendor.enabled:
                new_vendors.append(vendor)

        return {'item': item,
                'vendors': vendors,
                'new_vendors': new_vendors,
                'subtransactions': subtransactions}
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
                item_num  = request.POST['item-vendor-item_num-'+fields[3]]

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
                else:
                    val = request.POST[key]

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

    for x_ind in range(5):
        for y_ind in range(10):
            x_off = x + x_ind * (x_label + x_interlabel) + label_padding - x_hack
            y_off = y - y_ind * (y_label + y_interlabel) - barcode_height - label_padding

            print("x_off {} ({}) y_off {} ({})".format(x_off, x_off / inch, y_off, y_off / inch))

            barcode = code93.Extended93(item.barcode)
            print(barcode.minWidth())
            print(barcode.minWidth() / inch)
            barcode.drawOn(c, x_off, y_off)

            x_text = x_off + 6.4 * mm
            y_text = y_off - 5 * mm
            c.setFont("Helvetica", 12)
            c.drawString(x_text, y_text, item.barcode)

            y_text = y_text - 5 * mm
            c.setFont("Helvetica", 8)
            c.drawString(x_text, y_text, item.name)

    c.showPage()
    c.save()

    response = FileResponse(fname, request=request)
    return response


@view_config(route_name='admin_boxes_add',
             renderer='templates/admin/boxes_add.jinja2',
             permission='manage')
def admin_boxes_add(request):
    if len(request.GET) == 0:
        return {'items': {'count': 1,
                          'name-0': '',
                          'barcode-0': '',
                         }}
    else:
        return {'items': request.GET}


@view_config(route_name='admin_boxes_add_submit',
             request_method='POST',
             permission='manage')
def admin_boxes_add_submit(request):
    count = 0
    error_items = []

    # Iterate all the POST keys and find the ones that are item names
    for key in request.POST:
        if 'item-name-' in key:
            id = int(key.split('-')[2])
            stock = 0
            wholesale = 0
            price = 0
            enabled = False

            # Parse out the important fields looking for errors
            try:
                name = request.POST['item-name-{}'.format(id)]
                barcode = request.POST['item-barcode-{}'.format(id)]

                # Check that name and barcode are not blank. If name is blank
                # treat this as an empty row and skip. If barcode is blank
                # we will get a database error so send that back to the user.
                if name == '':
                    continue
                if barcode == '':
                    request.session.flash('Error adding item "{}". Barcode cannot be blank.'.format(name), 'error')
                    error_items.append({
                        'name': name, 'barcode': ''
                    })
                    continue

                # Add the item to the DB
                box = Box(name, barcode)
                DBSession.add(box)
                DBSession.flush()
                count += 1
            except:
                if len(name):
                    error_items.append({
                            'name' : request.POST['item-name-{}'.format(id)],
                            'barcode' : request.POST['item-barcode-{}'.format(id)]
                            })
                    request.session.flash('Error adding box: {}. Most likely a duplicate barcode.'.\
                                    format(name), 'error')
                # Otherwise this was probably a blank row; ignore.
    if count:
        request.session.flash('{} box{} added successfully.'.format(count, ['es',''][count==1]), 'success')
    else:
        request.session.flash('No boxes added.', 'error')
    if len(error_items):
        flat = {}
        e_count = 0
        for err in error_items:
            for k,v in err.items():
                flat['{}-{}'.format(k, e_count)] = v
            e_count += 1
        flat['count'] = len(error_items)
        return HTTPFound(location=request.route_url('admin_boxes_add', _query=flat))
    else:
        return HTTPFound(location=request.route_url('admin_boxes_edit'))


@view_config(route_name='admin_boxes_edit',
             renderer='templates/admin/boxes_edit.jinja2',
             permission='manage')
def admin_boxes_edit(request):
    boxes_active = Box.get_enabled()
    boxes_inactive = Box.get_disabled()
    boxes = boxes_active + boxes_inactive
    return {'boxes': boxes}


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
                val = request.POST[key]

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
        items = Item.all()

        # Don't display items that already have an item number in the add
        # new item section
        used_items = []
        #if hasattr(box, 'items'):
        for boxitem in box.items:
            if boxitem.enabled:
                used_items.append(boxitem.item_id)
        new_items = []
        for item in items:
            if item.id not in used_items and item.enabled:
                new_items.append(item)

        return {'box': box, 'items': items, 'new_items': new_items}
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
                quantity = request.POST['box-item-quantity-'+fields[3]]

                for boxitem in box.items:
                    # Update the BoxItem record.
                    # If the item quantity blank, set the record to disabled
                    # and do not update the quantity.
                    if boxitem.item_id == item_id and boxitem.enabled:
                        if quantity == '':
                            boxitem.enabled = False
                        else:
                            boxitem.quantity = int(quantity)
                        break
                else:
                    if quantity != '':
                        # Add a new vendor to the item
                        item = Item.from_id(item_id)
                        box_item = BoxItem(box, item, quantity)
                        DBSession.add(box_item)

            else:
                # Update the base item
                field = fields[1]
                if field == 'wholesale':
                    val = round(float(request.POST[key]), 2)
                elif field == 'quantity':
                    val = int(request.POST[key])
                else:
                    val = request.POST[key]

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
    
    except:
        request.session.flash('Error updating box.', 'error')
        return HTTPFound(location=request.route_url('admin_box_edit', box_id=int(request.POST['box-id'])))


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
        vendors[fields[2]][fields[1]] = request.POST[key]

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
        val = request.POST[key]

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
        reason = request.POST['reason']
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
        text = render('templates/admin/email_deadbeats.jinja2', {'user': deadbeat})
        print(text)

    request.session.flash('Deadbeat users emailed.', 'success')
    return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_users_email_all',
             request_method='POST',
             permission='admin')
def admin_users_email_all(request):
    users = User.all()
    text = request.POST['text']
    print(text)

    request.session.flash('All users emailed.', 'success')
    return HTTPFound(location=request.route_url('admin_index'))


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

    deposits = DBSession.query(BTCDeposit).order_by(desc(BTCDeposit.id)).all()
    cur_height = Bitcoin.get_block_height()

    transactions = []
    txhashes = {}
    for d in deposits:
        txhash = d.btctransaction
        btc_tx = Bitcoin.get_tx_by_hash(txhash)
        confirmations = (cur_height - btc_tx["block_height"] + 1) if "block_height" in btc_tx else 0

        true_amount = Decimal(0) # satoshis
        for output in btc_tx['out']:
            if output['addr'] == d.address and output['type'] == 0:
                true_amount += Decimal(output['value'])

        true_amount /= 100000000  # bitcoins

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

    res = Bitcoin.get_tx_from_addrs('|'.join(addrs))
    for tx in res['txs']:
        confirmations = (cur_height - tx['block_height'] + 1) if 'block_height' in tx else 0
        txhash = tx['hash']
        if txhash not in txhashes:
            # we found a btc deposit on the blockchain we didn't get a callback for!

            amount = Decimal(0)
            for output in tx['out']:
                if output['addr'] in addrs and output['type'] == 0:
                    addr = output['addr']
                    amount += Decimal(output['value'])

            amount /= 100000000

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
        bitcoin_usd = Bitcoin.convert_all()
        datalayer.reconcile_bitcoins(bitcoin_usd, request.user)
        request.session.flash('Converted Bitcoins to USD', 'success')
    except:
        request.session.flash('Error converting bitcoins', 'error')

    return HTTPFound(location=request.route_url('admin_index'))


@view_config(route_name='admin_events',
             renderer='templates/admin/events.jinja2',
             permission='manage')
def admin_events(request):
    events = Event.all()
    return {'events': events}


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
        receipt = request.POST['event-receipt'].file.read()
        datalayer.upload_receipt(event, request.user, receipt)
        return HTTPFound(location=request.route_url('admin_event',
                         event_id=int(request.POST['event-id'])))

    except Exception as e:
        if request.debug: raise(e)
        request.session.flash('Error', 'error')
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
    # Lookup the transaction that the user wants to undo
    try:
        event = Event.from_id(request.matchdict['event_id'])
    except:
        request.session.flash('Error: Could not find transaction to undo.', 'error')
        return HTTPFound(location=request.route_url('admin_events'))

    # Make sure its not already deleted
    if event.deleted:
        request.session.flash('Error: transaction already deleted', 'error')
        return HTTPFound(location=request.route_url('admin_events'))

    for transaction in event.transactions:
        # Make sure transaction is a deposit (no user check since admin doing)
        if transaction.type not in ('deposit', 'purchase'):
            request.session.flash('Error: Only deposits and purchases may be undone.', 'error')
            return HTTPFound(location=request.route_url('admin_events'))

    # If the checks pass, actually revert the transaction
    try:
        line_items = datalayer.undo_event(event, request.user)
        request.session.flash('Transaction successfully reverted.', 'success')
    except:
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


@view_config(route_name='admin_requests_delete',
             renderer='json',
             permission='admin')
def admin_requests_delete(request):
    try:
        request_id = int(request.matchdict['request_id'])
        request = Request.from_id(request_id)
        request.enabled = False
        return {'status':     'success',
                'request_id': request_id}
    except:
        return {'status': 'error'}


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
        announcements[fields[2]][fields[1]] = request.POST[key]

    for announcement_id, props in announcements.items():
        if announcement_id == 'new':
            if props['text'] == '':
                # Don't add blank announcements
                continue
            announcement = Announcement(request.user, props['text'])
            DBSession.add(announcement)
        else:
            announcement = Announcement.from_id(int(announcement_id))
            if not int(props['enabled']):
                announcement.enabled = False
            else:
                announcement.announcement = props['text']

    request.session.flash('Announcements updated successfully.', 'success')
    return HTTPFound(location=request.route_url('admin_announcements_edit'))


@view_config(route_name='admin_tweet_submit',
             request_method='POST',
             permission='admin')
def admin_tweet_submit(request):

    message = request.POST['tweet']

    twitterapi = twitter.api.Api(
        consumer_key=request.registry.settings['twitter.api_key'],
        consumer_secret=request.registry.settings['twitter.api_secret'],
        access_token_key=request.registry.settings['twitter.access_token'],
        access_token_secret=request.registry.settings['twitter.access_token_secret'])

    twitterapi.PostUpdate(message)

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
