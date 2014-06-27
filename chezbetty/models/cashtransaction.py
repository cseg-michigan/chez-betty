from .model import *

class CashAccount(Base):
    __tablename__ = "cash_accounts"
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    balance = Column(Float, nullable=False)
    
    def __init__(self, name):
        self.name = name
        self.balance = 0.0


def __make_cash_account(name):
    t = DBSession.query(CashAccount).filter(CashAccount.name == name).first()
    if t:
        return t
    t = CashAccount(name)
    DBSession.add(t)
    return t

# cash accounts
c_cashbox = __make_cash_account("cashbox")
c_chezbetty = __make_cash_account("chezbetty")
c_store = __make_cash_account("store")
c_lost = __make_cash_account("lost")



class CashTransaction(Base):
    __tablename__ = 'cash_transactions'

    id = Column(Integer, primary_key=True, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, unique=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)
    amount = Column(Float, nullable=False)

    to_account_id = Column(Integer, ForeignKey("cash_accounts.id"), nullable=False)
    from_account_id = Column(Integer, ForeignKey("cash_accounts.id"), nullable=False)
    
    to_account = relationship(CashAccount, 
        foreign_keys=[to_account_id,],
        backref="transactions_to"
    )
    
    from_account = relationship(CashAccount, 
        foreign_keys=[from_account_id,],
        backref="transactions_from"
    )
    
    def __init__(self, from_account, to_account, amount, transaction):
        self.from_account_id = from_account.id if from_account else None
        self.to_account_id = to_account.id if to_account else None
        self.amount = amount
        self.transaction_id = transaction.id if transaction else None
        to_acct.balance += amount
        from_acct.balance -= amount
           
    def __str__(self):
        return "<CashTransaction (%i: %s -> %s: $%f)>" % (
                self.id,
                self.from_account_id.name,
                self.to_account.name,
                self.amount)
                
                
class CashDeposit(CashTransaction):
    def __init__(self, amount, transaction):
        return CashTransaction.__init__(None, c_cashbox, amount, transaction)
