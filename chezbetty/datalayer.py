from .model import *

# cash accounts
c_cashbox = make_cash_account("cashbox")
c_chezbetty = make_cash_account("chezbetty")
c_store = make_cash_account("store")
c_lost = make_cash_account("lost")

def __transfer_cash(from_acct, to_acct, amount, transaction):
    from_acct.balance -= amount
    to_acct.balance += amount
    c = CashTransaction(
        from_account_id = from_acct.id if from_acct else None,
        to_account_id = to_acct.id if to_acct else None,
        amount = amount,
        transaction_id = transaction.id if transaction else None
    )

def deposit(user, amount):
    assert(amount > 0.0)
    assert(hasattr(user, "id"))
    transfer_cash(
        from_acct = None,
        to_account = c_cashbox,
        amount = amount,
        transaction_id=None
    )


def purchase(user, items):
    assert(hasattr(user, "id"))
    t = Purchase(user)
    DBSession.add(p)
    amount = 0.0
    for item, quantity in items.items():
        st = SubTransaction(p, item, quantity)
        t.amount += st.amount
    user.balance -= 
    return t





def reconcile_items(items):
    for item, quantity in items.items():


def reconcile_cash(amount):
    pass
    
