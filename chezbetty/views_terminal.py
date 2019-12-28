from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.view import view_config, forbidden_view_config

from pyramid.i18n import TranslationStringFactory, get_localizer
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
from .models.tag import Tag
from .models.ephemeron import Ephemeron
from .models.badscan import BadScan

from .utility import user_password_reset
from .utility import send_email

from pyramid.security import Allow, Everyone, remember, forget

import chezbetty.datalayer as datalayer
import transaction

import math


# The amount of debt a user must have before automatic emails on purchases are sent
global debtor_email_theshold
debtor_email_theshold = Decimal(-5.00)

# Custom exception
class DepositException(Exception):
    pass


# Check for a valid user by UMID.
#
# Input: form encoded umid=11223344
#
# Note: will not create new user if this user does not exist.
@view_config(route_name='terminal_umid_check',
             request_method='POST',
             renderer='json',
             permission='service')
def terminal_umid_check(request):
    try:
        user = User.from_umid(request.POST['umid'])
        if user.role == 'serviceaccount':
            # n.b. don't expose a different error path here
            raise User.InvalidUserException
        return {}
    except:
        return {'error': get_localizer(request).translate(
                    _('mcard-keypad-error',
                      default='First time using Betty? You need to swipe your M-Card the first time you log in.'))}


## Main terminal page with purchase/cash deposit.
@view_config(route_name='terminal',
             renderer='templates/terminal/terminal.jinja2',
             permission='service')
def terminal(request):
    try:
        if len(request.matchdict['umid']) != 8:
            raise __user.InvalidUserException()

        with transaction.manager:
            user = User.from_umid(request.matchdict['umid'], create_if_never_seen=True)
        user = DBSession.merge(user)
        if not user.enabled:
            request.session.flash(get_localizer(request).translate(_(
                'user-not-enabled',
                default='User is not enabled. Please contact ${email}.',
                mapping={'email':request.registry.settings['chezbetty.email']},
                )), 'error')
            return HTTPFound(location=request.route_url('index'))

        # Handle re-instating archived user
        if user.archived:
            if user.archived_balance != 0:
                datalayer.adjust_user_balance(user,
                                              user.archived_balance,
                                              'Reinstated archived user.',
                                              request.user)
            user.balance = user.archived_balance
            user.archived = False

        # NOTE TODO (added on 2016/05/14): The "name" field in this temp
        # table needs to be terminal specific. That is, if there are multiple
        # terminals, items and money shouldn't be able to move between them.

        # If cash was added before a user was logged in, credit that now
        deposit = None
        in_flight_deposit = Ephemeron.from_name('deposit')
        if in_flight_deposit:
            amount = Decimal(in_flight_deposit.value)
            deposit = datalayer.deposit(user, user, amount)
            DBSession.delete(in_flight_deposit)

        # For Demo mode:
        items = DBSession.query(Item)\
                         .filter(Item.enabled == True)\
                         .order_by(Item.name)\
                         .limit(6).all()

        # Determine initial wall-of-shame fee (if applicable)
        purchase_fee_percent = Decimal(0)
        if user.balance <= Decimal('-5.0') and user.role != "administrator":
            purchase_fee_percent = 5 + (math.floor((user.balance+5) / -5) * 5)

        # Figure out if any pools can be used to pay for this purchase
        purchase_pools = []
        for pool in Pool.all_by_owner(user, True):
            if pool.balance > (pool.credit_limit * -1):
                purchase_pools.append(pool)

        for pu in user.pools:
            if pu.enabled and pu.pool.enabled and pu.pool.balance > (pu.pool.credit_limit * -1):
                purchase_pools.append(pu.pool)

        # Get the list of tags that have items without barcodes in them
        tags_with_nobarcode_items = Tag.get_tags_with_nobarcode_items();

        return {'user': user,
                'items': items,
                'purchase_pools': purchase_pools,
                'purchase_fee_percent': purchase_fee_percent,
                'good_standing_discount': round((datalayer.good_standing_discount)*100),
                'good_standing_volunteer_discount': round((datalayer.good_standing_volunteer_discount)*100),
                'good_standing_manager_discount': round((datalayer.good_standing_manager_discount)*100),
                'admin_discount': round((datalayer.admin_discount)*100),
                'tags_with_nobarcode_items': tags_with_nobarcode_items,
                'nobarcode_notag_items': Item.get_nobarcode_notag_items(),
                'deposit': deposit}

    except __user.InvalidUserException as e:
        request.session.flash(get_localizer(request).translate(_(
            'mcard-error',
            default='Failed to read M-Card. Please try swiping again.',
            )), 'error')
        return HTTPFound(location=request.route_url('index'))


## Get all items without barcodes in a tag
@view_config(route_name='terminal_purchase_tag',
             renderer='json',
             permission='service')
def terminal_purchase_tag(request):
    try:
        tag_id = int(request.matchdict['tag_id'])
        tag = Tag.from_id(tag_id)
    except:
        if request.matchdict['tag_id'] == 'other':
            tag = {'name': 'other',
                   'nobarcode_items': Item.get_nobarcode_notag_items()}
        else:
            return {'error': 'Unable to parse TAG ID'}

    item_array = render('templates/terminal/purchase_nobarcode_items.jinja2',
                        {'tag': tag})

    return {'items_html': item_array}


## Add a cash deposit.
@view_config(route_name='terminal_deposit',
             request_method='POST',
             renderer='json',
             permission='service')
def terminal_deposit(request):
    try:
        if request.POST['umid'] == '':
            # User was not logged in when deposit was made. We store
            # this deposit temporarily and give it to the next user who
            # logs in.
            user = None
        else:
            user = User.from_umid(request.POST['umid'])
        amount = Decimal(request.POST['amount'])
        method = request.POST['method']

        # Can't deposit a negative amount
        if amount <= 0.0:
            raise DepositException('Deposit amount must be greater than $0.00')

        # Now check the deposit method. We trust anything that comes from the
        # bill acceptor, but double check a manual deposit
        if method == 'manual':
            # Check if the deposit amount is too great.
            if amount > 2.0:
                # Anything above $2 is blocked
                raise DepositException('Deposit amount of ${:,.2f} exceeds the limit'.format(amount))

        elif method == 'acceptor':
            # Any amount is OK
            pass

        else:
            raise DepositException('"{}" is an unknown deposit type'.format(method))

        # At this point the deposit can go through
        ret = {}

        if user:
            deposit = datalayer.deposit(user, user, amount, method != 'manual')
            ret['type'] = 'user'
            ret['amount'] = float(deposit['amount'])
            ret['event_id'] = deposit['event'].id
            ret['user_balance'] = float(user.balance)

        else:
            # No one was logged in. Need to save this temporarily
            # total_stored = datalayer.temporary_deposit(amount);
            # ret['type'] = 'temporary'
            # ret['new_amount'] = float(amount)
            # ret['total_amount'] = float(total_stored)

            print('GOT NON-LOGGED IN DEPOSIT')
            print('GOT NON-LOGGED IN DEPOSIT')
            print('GOT NON-LOGGED IN DEPOSIT')
            print('AMOUNT: {}'.format(amount))
            print('IGNORING THIS FOR NOW.')
            ret['error'] = 'Must be logged in to deposit'

        return ret

    except __user.InvalidUserException as e:
        request.session.flash('Invalid user error. Please try again.', 'error')
        return {'error': 'Error finding user.'}

    except ValueError as e:
        return {'error': 'Error understanding deposit amount.'}

    except DepositException as e:
        return {'error': str(e)}

    except Exception as e:
        return {'error': str(e)}


def get_item_from_barcode(barcode):
    try:
        item = Item.from_barcode(barcode)
    except:
        # Could not find the item. Check to see if the user scanned a box
        # instead. This could lead to two cases: a) the box only has 1 item in it
        # in which case we just add that item to the cart. This likely occurred
        # because the individual items do not have barcodes so we just use
        # the box. b) The box has multiple items in it in which case we throw
        # an error for now.
        try:
            box = Box.from_barcode(barcode)
            if box.subitem_number == 1:
                item = box.items[0].item
            else:
                return 'Cannot add that entire box to your order. Please scan an individual item.'
        except:
            badscan = BadScan(barcode)
            DBSession.add(badscan)
            DBSession.flush()

            return 'Could not find that item.'

    if not item.enabled:
        return 'That product is not currently for sale.'

    return item


## Get details about an item based on a barcode. This can be used to add to a
## cart or as a price check.
@view_config(route_name='terminal_item_barcode',
             renderer='json',
             permission='service')
def terminal_item_barcode(request):
    item = get_item_from_barcode(request.matchdict['barcode'])

    if type(item) is str:
         return {'error': item}

    item_html = render('templates/terminal/purchase_item_row.jinja2', {'item': item})
    return {'id': item.id,
            'name': item.name,
            'price': float(item.price),
            'item_row_html': item_html}


## Get details about an item based on an item ID. This can be used to add to a
## cart or as a price check.
@view_config(route_name='terminal_item_id',
             renderer='json',
             permission='service')
def terminal_item_id(request):
    try:
        item = Item.from_id(request.matchdict['item_id'])
    except:
        return {'error': 'Could not find that item.'}

    if not item.enabled:
        return {'error': 'That product is not currently for sale.'}

    item_html = render('templates/terminal/purchase_item_row.jinja2', {'item': item})
    return {'id': item.id,
            'name': item.name,
            'price': float(item.price),
            'item_row_html': item_html}


## Make a purchase from the terminal.
@view_config(route_name='terminal_purchase',
             request_method='POST',
             renderer='json',
             permission='service')
def terminal_purchase(request):
    try:
        user = User.from_umid(request.POST['umid'])

        ignored_keys = ['umid', 'pool_id']

        # Bundle all purchase items
        items = {}
        for item_id,quantity in request.POST.items():
            if item_id in ignored_keys:
                continue
            item = Item.from_id(int(item_id))
            items[item] = int(quantity)

        # What should pay for this?
        # Note: should do a bunch of checking to make sure all of this
        # is kosher. But given our locked down single terminal, we're just
        # going to skip all of that.
        if 'pool_id' in request.POST:
            pool = Pool.from_id(int(request.POST['pool_id']))
            purchase = datalayer.purchase(user, pool, items)
        else:
            purchase = datalayer.purchase(user, user, items)

        # Create a order complete view
        order = {'total': purchase.amount,
                 'discount': purchase.discount,
                 'items': []}
        for subtrans in purchase.subtransactions:
            item = {}
            item['name'] = subtrans.item.name
            item['quantity'] = subtrans.quantity
            item['price'] = subtrans.item.price
            item['total_price'] = subtrans.amount
            order['items'].append(item)

        if purchase.fr_account_virt_id == user.id:
            account_type = 'user'
            pool = None
        else:
            account_type = 'pool'
            pool = Pool.from_id(purchase.fr_account_virt_id)

        # Email the user if they are currently in debt
        if float(user.balance) < debtor_email_theshold:
            send_email(
                TO=user.uniqname+'@umich.edu',
                SUBJECT='Please Pay Your Chez Betty Balance',
                body=render('templates/terminal/email_user_in_debt.jinja2',
                {'user': user})
                )

        summary = render('templates/terminal/purchase_complete.jinja2',
            {'user': user,
             'event': purchase.event,
             'order': order,
             'transaction': purchase,
             'account_type': account_type,
             'pool': pool})

        # Return the committed transaction ID
        return {'order_table': summary,
                'user_balance': float(user.balance)}

    except __user.InvalidUserException as e:
        return {'error': get_localizer(request).translate(_('invalid-user-error',
                           default='Invalid user error. Please try again.'))
               }

    except ValueError as e:
        return {'error': 'Unable to parse Item ID or quantity'}

    except NoResultFound as e:
        # Could not find an item
        return {'error': 'Unable to identify an item.'}


## Delete a just completed purchase.
@view_config(route_name='terminal_purchase_delete',
             request_method='POST',
             renderer='json',
             permission='service')
def terminal_purchase_delete(request):
    try:
        user = User.from_umid(request.POST['umid'])
        old_event = Event.from_id(request.POST['old_event_id'])

        if old_event.type != 'purchase' or \
           old_event.transactions[0].type != 'purchase' or \
           (old_event.transactions[0].fr_account_virt_id != user.id and \
            old_event.user_id != user.id):
           # Something went wrong, can't undo this purchase
           raise DepositException('Cannot undo that purchase')

        # Now undo old deposit
        datalayer.undo_event(old_event, user)

        return {'user_balance': float(user.balance)}

    except __user.InvalidUserException as e:
        return {'error': 'Invalid user error. Please try again.'}

    except DepositException as e:
        return {'error': str(e)}
