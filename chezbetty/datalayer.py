from .models import *
from .models.transaction import *
from .models.cashtransaction import *

def undo_transaction(t):
    if t.to_account:
        t.to_account.balance -= t.amount
    if t.from_account:
        t.from_account.balance += t.amount
    if t.cash_transaction:
        c_to_acct = t.cash_transaction.to_account
        if c_to_acct:
            c_to_acct.balance -= t.cash_transaction.amount
        c_from_acct = t.cash_transaction.from_account
        if c_from_acct:
            c_from_acct.balance += t.cash_transaction.amount
        DBSession.delete(t.cash_transaction)

    DBSession.delete(t)

def deposit(user, amount):
    assert(amount > 0.0)
    assert(hasattr(user, "id"))
    prev = user.balance
    t = Deposit(user, amount)
    DBSession.add(t)
    c = CashDeposit(amount, t)
    DBSession.add(c)
    return dict(prev=prev, new=user.balance, amount=amount,
            transaction=t, cash_transaction=c)


def bitcoin_deposit(user, amount, btc_transaction):
    assert(amount > 0.0)
    assert(hasattr(user, "id"))
    prev = user.balance
    t = BTCDeposit(user, amount, btc_transaaction)
    DBSession.add(t)
    c = BTCCashDeposit(amount, t)
    DBSession.add(c)
    return dict(prev=prev, new=user.balance, amount=amount,
            transaction=t, cash_transaction=c)


def adjust_user_balance(user, adjustment, notes, admin=None):
    assert(hasattr(user, "id"))
    t = Adjustment(user, adjustment, notes, admin)
    DBSession.add(t)

def purchase(user, items):
    assert(hasattr(user, "id"))
    assert(len(items) > 0)
    t = Purchase(user)
    DBSession.add(t)
    DBSession.flush()
    amount = 0.0
    for item, quantity in items.items():
        item.in_stock -= quantity
        st = SubTransaction(t, item, quantity, item.wholesale)
        DBSession.add(st)
        amount += st.amount
    t.update_amount(amount)
    return t

def restock(items, admin=None):
    t = Restock(user)
    DBSession.add(t)
    DBSession.flush()
    amount = 0.0
    for item, quantity in items.items():
        item.in_stock += quantity
        item.enabled = True
        st = SubTransaction(t, item, quantity, item.wholesale)
        DBSession.add(st)
        amount += st.amount
    t.update_amount(amount)
    return t


def reconcile_items(items, admin):
    t = Reconciliation(admin)
    total_amount_missing = 0.0
    for item, quantity in items.items():
        if item.in_stock == quantity:
            continue
        quantity_missing = item.in_stock - quantity
        st = SubTransaction(t, item, quantity_missing, item.wholesale)
        total_amount_missing += st.amount
        item.in_stock = quantity
    t.update_amount(total_amount_missing)
    return t

def reconcile_cash(amount, admin):
    cashbox = make_cash_account("cashbox")
    expected_amount = cashbox.balance
    amount_missing = expected_amount - amount
    cashbox.balance = 0

    t = CashTransaction(
        from_account = make_cash_account("cashbox"),
        to_account = make_cash_account("chezbetty"),
        amount = amount,
        transaction = None,
        user = admin
    )
    DBSession.add(t)
    if amount_missing != 0.0:
        t2 = CashTransaction(
            from_account = make_cash_account("cashbox"),
            to_account = make_cash_account("lost"),
            amount = amount_missing,
            transaction = None,
            user = admin
        )
        DBSession.add(t2)
    return expected_amount

