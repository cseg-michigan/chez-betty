from .models import *

def deposit(user, amount):
    assert(amount > 0.0)
    assert(hasattr(user, "id"))
    t = Deposit(user, amount)
    DBSession.add(t)
    c = CashDeposit(amount, t)
    DBSession.add(c)

def purchase(user, items):
    assert(hasattr(user, "id"))
    assert(len(items) > 0)
    t = Purchase(user)
    DBSession.add(p)
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
        

def reconcile_cash(amount):
    pass
    
