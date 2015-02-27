from .models.model import *
from .models import event
from .models import transaction
from .models import account
from .models import request
from .models import receipt
from .models.item import Item
from .models.box import Box
from .models import box_item
from .models import item_vendor
from .models import box_vendor

def can_undo_event(e):
    if e.type != 'deposit' and e.type != 'purchase' and e.type != 'restock' \
       and e.type != 'inventory':
        return False
    if e.deleted:
        return False
    return True


# Call this to remove an event from chez betty. Only works with cash deposits
def undo_event(e, user):
    assert(can_undo_event(e))

    line_items = {}

    for t in e.transactions:

        if t.to_account_virt:
            t.to_account_virt.balance -= t.amount
        if t.fr_account_virt:
            t.fr_account_virt.balance += t.amount
        if t.to_account_cash:
            t.to_account_cash.balance -= t.amount
        if t.fr_account_cash:
            t.fr_account_cash.balance += t.amount

        if t.type == 'purchase':
            # Re-add the stock to the items that were purchased
            for s in t.subtransactions:
                line_items[s.item_id] = s.quantity
                Item.from_id(s.item_id).in_stock += s.quantity

        elif t.type == 'restock':
            # Add all of the boxes and items to the return list
            # Also remove the stock this restock added to each item
            for i,s in zip(range(len(t.subtransactions)), t.subtransactions):
                if s.type == 'restocklineitem':
                    item = Item.from_id(s.item_id)
                    line_items[i] = '{},{},{},{},{},{},{}'.format(
                        'item', s.item_id, s.quantity, s.wholesale,
                        s.coupon_amount, s.sales_tax, s.bottle_deposit)
                    item.in_stock -= s.quantity
                elif s.type == 'restocklinebox':
                    line_items[i] = '{},{},{},{},{},{},{}'.format(
                        'box', s.box_id, s.quantity, s.wholesale,
                        s.coupon_amount, s.sales_tax, s.bottle_deposit)
                    for ss in s.subsubtransactions:
                        item = Item.from_id(ss.item_id)
                        item.in_stock -= ss.quantity

        elif t.type == 'inventory':
            # Change the stock of all the items by reversing the inventory count
            for s in t.subtransactions:
                quantity_diff = s.quantity - s.quantity_counted
                s.item.in_stock += quantity_diff
                line_items[s.item_id] = s.quantity_counted

    # Just need to delete the event. All transactions will understand they
    # were deleted as well.
    e.delete(user)

    return line_items

def can_delete_item(item):
    if len(item.boxes) == 0 and\
       len(item.vendors) == 0 and\
       len(item.subtransactions) == 0 and\
       len(item.subsubtransactions) == 0:
       return True
    return False

def delete_item(item):
    boxitems = DBSession.query(box_item.BoxItem).filter(box_item.BoxItem.item_id==item.id).all()
    for bi in boxitems:
        DBSession.delete(bi)
    itemvendors = DBSession.query(item_vendor.ItemVendor).filter(item_vendor.ItemVendor.item_id==item.id).all()
    for iv in itemvendors:
        DBSession.delete(iv)
    DBSession.delete(item)

def can_delete_box(box):
    if len(box.items) == 0 and\
       len(box.vendors) == 0 and\
       len(box.subtransactions) == 0:
       return True
    return False

def delete_box(box):
    boxitems = DBSession.query(box_item.BoxItem).filter(box_item.BoxItem.box_id==box.id).all()
    for bi in boxitems:
        DBSession.delete(bi)
    boxvendors = DBSession.query(box_vendor.BoxVendor).filter(box_vendor.BoxVendor.box_id==box.id).all()
    for bv in boxvendors:
        DBSession.delete(bv)
    DBSession.delete(box)


# Call this to make a new item request
def new_request(user, request_text):
    r = request.Request(user, request_text)
    DBSession.add(r)
    DBSession.flush()
    return r


# Call this to let a user purchase items
def purchase(user, account, items):
    assert(hasattr(user, "id"))
    assert(len(items) > 0)

    # TODO: Parameterize
    discount = Decimal(0.05) if user.balance > 20.0 else None

    e = event.Purchase(user)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Purchase(e, account, discount)
    DBSession.add(t)
    DBSession.flush()
    amount = Decimal(0.0)
    for item, quantity in items.items():
        item.in_stock -= quantity
        line_amount = Decimal(item.price * quantity)
        pli = transaction.PurchaseLineItem(t, line_amount, item, quantity,
                                           item.price, item.wholesale)
        DBSession.add(pli)
        amount += line_amount
    if discount:
        amount = amount - (amount * discount)
    t.update_amount(amount)
    return t


# Call this when a user puts money in the dropbox and needs to deposit it
# to their account
def deposit(user, account, amount):
    assert(amount > 0.0)
    assert(hasattr(user, "id"))

    prev = user.balance
    e = event.Deposit(user)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.CashDeposit(e, account, amount)
    DBSession.add(t)
    return dict(prev=prev,
                new=user.balance,
                amount=amount,
                transaction=t,
                event=e)


# Call this to deposit bitcoins to the user account
def bitcoin_deposit(user, amount, btc_transaction, address, amount_btc):
    assert(amount > 0.0)
    assert(hasattr(user, "id"))

    prev = user.balance
    e = event.Deposit(user)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.BTCDeposit(e, user, amount, btc_transaction, address, amount_btc)
    DBSession.add(t)
    return dict(prev=prev,
                new=user.balance,
                amount=amount,
                transaction=t)


# Call this to adjust a user's balance
def adjust_user_balance(user, adjustment, notes, admin):
    e = event.Adjustment(admin, notes)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Adjustment(e, user, adjustment)
    DBSession.add(t)
    return t


# Call this when an admin restocks chezbetty
def restock(items, admin, timestamp=None):
    e = event.Restock(admin, timestamp)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Restock(e)
    DBSession.add(t)
    DBSession.flush()
    amount = Decimal(0.0)

    # Add all of the items as subtransactions
    for thing, quantity, total, wholesale, coupon, salestax, btldeposit in items:
        if type(thing) is Item:
            item = thing
            # Add the stock to the item
            item.in_stock += quantity
            # Make sure the item is enabled (now that we have some in stock)
            item.enabled = True
            # Create a subtransaction to track that this item was added
            rli = transaction.RestockLineItem(t, total, item, quantity, wholesale, coupon, salestax, btldeposit)
            DBSession.add(rli)
            #amount += Decimal(total)

        elif type(thing) is Box:
            box = thing

            # Create a subtransaction to record that the box was restocked
            rlb = transaction.RestockLineBox(t, total, box, quantity, wholesale, coupon, salestax, btldeposit)
            DBSession.add(rlb)
            DBSession.flush()

            # Iterate all the subitems and update the stock
            for itembox in box.items:
                subitem = itembox.item
                subquantity = itembox.quantity * quantity
                subitem.enabled = True
                subitem.in_stock += subquantity

                rlbi = transaction.RestockLineBoxItem(rlb, subitem, subquantity)
                DBSession.add(rlbi)

        amount += Decimal(total)

    t.update_amount(amount)
    return e


# Call this when a user runs inventory
def reconcile_items(items, admin):
    e = event.Inventory(admin)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Inventory(e)
    DBSession.add(t)
    DBSession.flush()
    total_amount_missing = Decimal(0.0)
    for item, quantity in items.items():
        # Record the restock line item even if the number hasn't changed.
        # This lets us track when we have counted items.
        quantity_missing = item.in_stock - quantity
        line_amount = quantity_missing * item.wholesale
        ili = transaction.InventoryLineItem(t, line_amount, item, item.in_stock,
                                quantity, item.wholesale)
        DBSession.add(ili)
        total_amount_missing += ili.amount
        item.in_stock = quantity
    t.update_amount(total_amount_missing)
    DBSession.add(t)
    DBSession.flush()
    return t


# Call this when the cash box gets emptied
def reconcile_cash(amount, admin):
    assert(amount>=0)

    e = event.EmptyCashBox(admin)
    DBSession.add(e)
    DBSession.flush()

    cashbox_c = account.get_cash_account("cashbox")
    expected_amount = cashbox_c.balance
    amount_missing = expected_amount - amount

    if amount_missing != 0.0:
        # If the amount in the cashbox doesn't match what we expected there to
        # be, we need to adjust the amount in the cash box be transferring
        # to or from a null account

        if amount_missing > 0:
            # We got less in the box than we expected
            # Move money from the cashbox account to null with transaction type
            # "lost"
            t1 = transaction.Lost(e, account.get_cash_account("cashbox"), amount_missing)
            DBSession.add(t1)

        else:
            # We got more in the box than expected! Use a found transaction
            # to reconcile the difference
            t1 = transaction.Found(e, account.get_cash_account("cashbox"), abs(amount_missing))
            DBSession.add(t1)


    # Now move all the money from the cashbox to chezbetty
    t2 = transaction.EmptyCashBox(e, amount)
    DBSession.add(t2)
    return expected_amount


# Call this to move money from the cash box to the bank, but without necessarily
# emptying the cash box.
def cashbox_to_bank(amount, admin):
    assert(amount>=0)

    e = event.EmptyCashBox(admin)
    DBSession.add(e)
    DBSession.flush()

    t = transaction.EmptyCashBox(e, amount)
    DBSession.add(t)
    

# Call this when bitcoins are converted to USD
def reconcile_bitcoins(amount, admin, expected_amount=None):
    assert(amount>0)

    e = event.EmptyBitcoin(admin)
    DBSession.add(e)
    DBSession.flush()

    btcbox_c = account.get_cash_account("btcbox")
    if expected_amount == None:
        expected_amount = btcbox_c.balance
    amount_missing = expected_amount - amount

    if amount_missing != 0.0:
        # Value of bitcoins fluctated and we didn't make as much as we expected

        if amount_missing > 0:
            # We got less in bitcoins than we expected
            # Move money from the btcbox account to null with transaction type
            # "lost"
            t1 = transaction.Lost(e, account.get_cash_account("btcbox"), amount_missing)
            DBSession.add(t1)

        else:
            # We got more in bitcoins than expected! Use a found transaction
            # to reconcile the difference
            t1 = transaction.Found(e, account.get_cash_account("btcbox"), abs(amount_missing))
            DBSession.add(t1)


    # Now move all the money from the bitcoin box to chezbetty
    t2 = transaction.EmptyBitcoin(e, amount)
    DBSession.add(t2)
    return expected_amount


# Call this to make a miscellaneous adjustment to the chezbetty account
def reconcile_misc(amount, notes, admin):
    assert(amount != 0.0)

    e = event.Reconcile(admin, notes)
    DBSession.add(e)
    DBSession.flush()

    if amount < 0.0:
        t = transaction.Lost(e, account.get_cash_account("chezbetty"), abs(amount))
    else:
        t = transaction.Found(e, account.get_cash_account("chezbetty"), amount)
    DBSession.add(t)
    return t


# Call this to make a cash donation to Chez Betty
def add_donation(amount, notes, admin):
    e = event.Donation(admin, notes)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Donation(e, amount)
    DBSession.add(t)
    return t


# Call this to withdraw cash funds from Chez Betty into another account
def add_withdrawal(amount, notes, admin):
    e = event.Withdrawal(admin, notes)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Withdrawal(e, amount)
    DBSession.add(t)
    return t

def upload_receipt(event, admin, rfile):
    r = receipt.Receipt(event, admin, rfile)
    DBSession.add(r)
    DBSession.flush()
    return r
