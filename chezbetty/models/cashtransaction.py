from .model import *

class CashAccount(Base):
    __tablename__ = "cash_accounts"
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    balance = Column(Float, nullable=False)
    
    def __init__(self, name):
        self.name = name
        self.balance = 0.0


def make_cash_account(name):
    t = DBSession.query(CashAccount).filter(CashAccount.name == name).first()
    if t:
        return t
    t = CashAccount(name)
    DBSession.add(t)
    DBSession.flush()
    return t

class CashTransaction(Base):
    __tablename__ = 'cash_transactions'

    id = Column(Integer, primary_key=True, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, unique=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)
    amount = Column(Float, nullable=False)

    to_account_id = Column(Integer, ForeignKey("cash_accounts.id"))
    from_account_id = Column(Integer, ForeignKey("cash_accounts.id"))
    
    to_account = relationship(CashAccount, 
        foreign_keys=[to_account_id,],
        backref="transactions_to"
    )
    
    from_account = relationship(CashAccount, 
        foreign_keys=[from_account_id,],
        backref="transactions_from"
    )
    
    def __init__(self, from_account, to_account, amount, transaction, user):
        self.from_account_id = from_account.id if from_account else None
        self.to_account_id = to_account.id if to_account else None
        self.amount = amount
        self.transaction_id = transaction.id if transaction else None
        self.user_id = user.id if user else None
        if to_account:
            to_account.balance += amount
        if from_account:
            to_account.balance -= amount
           
    def __str__(self):
        return "<CashTransaction (%i: %s -> %s: $%f)>" % (
                self.id,
                self.from_account_id.name,
                self.to_account.name,
                self.amount)
                
                
class CashDeposit(CashTransaction):
    def __init__(self, amount, transaction):
        c_cashbox = make_cash_account("cashbox")
        assert(c_cashbox)
        assert(c_cashbox.id)
        CashTransaction.__init__(self, None, c_cashbox, amount, transaction, None)
        
