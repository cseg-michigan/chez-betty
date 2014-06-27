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
    t = DBSession.query(Account).filter(Account.name == "cashbox").first()
    if t:
        return t
    t = CashAccount(name)
    DBSession.add(t)
    return t


class CashTransaction(Base):
    __tablename__ = 'cash_transactions'

    id = Column(Integer, primary_key=True, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, unique=True)
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
    
    def __str__(self):
        return "<CashTransaction (%i: %s -> %s: $%f)>" % (
                self.id,
                self.from_account_id.name,
                self.to_account.name,
                self.amount)
