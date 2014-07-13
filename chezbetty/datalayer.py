from .models.model import *
from .models import event
from .models import transaction
from .models import account
from .models import request

def can_undo_event(e):
    return(e.type=='deposit' or e.type=='purchase')

# Call this to remove an event from chez betty. Only works with cash deposits
def undo_event(e):
    assert(can_undo_event(e))

    line_items = {}

    for t in e.transactions:

        assert(t.type=='deposit' or e.type=='purchase')

        if t.to_account_virt:
            t.to_account_virt.balance -= t.amount
        if t.fr_account_virt:
            t.fr_account_virt.balance += t.amount
        if t.to_account_cash:
            t.to_account_cash.balance -= t.amount
        if t.fr_account_cash:
            t.fr_account_cash.balance += t.amount

        for s in t.subtransactions:
            line_items[s.item_id] = s.quantity
            DBSession.delete(s)

        DBSession.delete(t)

    DBSession.delete(e)

    return line_items


# Call this to make a new item request
def new_request(user, request_text):
    r = request.Request(user, request_text)
    DBSession.add(r)
    DBSession.flush()
    return r


# Call this to let a user purchase items
def purchase(user, items):
    assert(hasattr(user, "id"))
    assert(len(items) > 0)

    e = event.Purchase(user)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Purchase(e, user)
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
    t.update_amount(amount)
    return t


# Call this when a user puts money in the dropbox and needs to deposit it
# to their account
def deposit(user, amount):
    assert(amount > 0.0)
    assert(hasattr(user, "id"))

    prev = user.balance
    e = event.Deposit(user)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Deposit(e, user, amount)
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
def restock(items, admin):
    e = event.Restock(admin)
    DBSession.add(e)
    DBSession.flush()
    t = transaction.Restock(e)
    DBSession.add(t)
    DBSession.flush()
    amount = Decimal(0.0)
    for item, quantity in items.items():
        item.in_stock += quantity
        item.enabled = True
        line_amount = quantity * item.wholesale
        rli = transaction.RestockLineItem(t, line_amount, item, quantity, item.wholesale)
        DBSession.add(rli)
        amount += rli.amount
    t.update_amount(amount)
    return t


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
        if item.in_stock == quantity:
            continue
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
    assert(amount>0)

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


# Call this when bitcoins are converted to USD
def reconcile_bitcoins(amount, admin):
    assert(amount>0)

    e = event.EmptyBitcoin(admin)
    DBSession.add(e)
    DBSession.flush()

    btcbox_c = account.get_cash_account("btcbox")
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
