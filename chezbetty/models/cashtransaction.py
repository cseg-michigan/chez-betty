from .model import *

class CashAccount(Base):
    __tablename__ = "cash_accounts"
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    balance = Column(Float, nullable=False)
    
    def __init__(self, name):
        self.name = name
        self.balance = 0.0

# singletons that 

def make_cash_account(name):
    t = DBSession.query(Account).filter(Account.name == "cashbox").first()
    if t:
        return t
    t = CashAccount(name)
    DBSession.add(t)
    return t

c_cashbox = make_cash_account("cashbox")
c_chezbetty = make_cash_account("chezbetty")
c_store = make_cash_account("store")
c_lost = make_cash_account("lost")

class CashTransaction(Base):
    __tablename__ = 'cash_transactions'

    id = Column(Integer, primary_key=True, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, unique=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)
    amount = Column(Float, nullable=False)

    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    

