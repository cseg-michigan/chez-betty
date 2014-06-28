from .models import *
from .models.transaction import *
from .models.cashtransaction import *

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


def purchase(user, items):
    assert(hasattr(user, "id"))
    assert(len(items) > 0)
    t = Purchase(user)
    DBSession.add(t)
    amount = 0.0
    for item, quantity in items.items():
        item.in_stock -= quantity
        st = SubTransaction(t, item, quantity)
        DBSession.add(st)
    t.update_amount(amount)
    return t


def reconcile_items(items, admin):
    t = Reconciliation(admin)
    total_amount_missing = 0.0
    for item, quantity in items.items():
        if item.quantity == quantity:
            continue
        quantity_missing = item.quantity - quantity
        st = SubTransaction(t, item, quantity_missing)
        total_amount_missing += st.amount
    t.update_amount(total_amount_missing)
        

def reconcile_cash(amount, admin):
    cash = DBSession.query(make_cash_account("cashbox"))
    expected_amount = cash.balance
    amount_missing = expected_amount - amount
    
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
    
