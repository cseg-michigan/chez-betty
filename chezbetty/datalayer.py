from .model import *



def deposit(user, amount):
    assert(amount > 0.0)
    assert(hasattr(user, "id"))
    t = Deposit(user, amount)
    DBSession.add(t)
    c = CashDeposit(amount, t)
    DBSession.add(c)

def purchase(user, items):
    assert(hasattr(user, "id"))
    t = Purchase(user)
    DBSession.add(p)
    amount = 0.0
    for item, quantity in items.items():
        st = SubTransaction(p, item, quantity)
        t.amount += st.amount
    user.balance -= -
    return t





def reconcile_items(items):
    for item, quantity in items.items():


def reconcile_cash(amount):
    pass
    
