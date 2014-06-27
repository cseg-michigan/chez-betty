from .model import *

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(Enum("purchase", "deposit", "reconcile", "administrative"), nullable=False)
    __mapper_args__ = {'polymorphic_on':type}
    
    to_account = relationship(Account, 
        foreign_keys=[to_account_id,],
        backref="transactions_to"
    )
    
    from_account = relationship(Acount, 
        foreign_keys=[from_account_id,],
        backref="transactions_from"
    )

    def __init__(self, from_account, to_account, amount):
        self.to_account_id = to_account.id
        self.from_account_id = from_account.id
        self.amount = amount

    def update_amount(self, amount):
        self.to_account -= self.amount
        self.from_account += self.amount
        self.amount = amount
        self.to_account += self.amount
        self.from_account -= self.amount


class Deposit(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'deposit'}

    def __init__(self, amount):
        Transaction.__init__(self, None, user, amount)


class Purchase(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'purchase'}
    def __init__(self, user):
        Transaction.__init__(self, user, chezbetty, 0.0)
        


class Reconcile(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'reconcile'}


class SubTransaction(Base):
    __tablename__ = "subtransactions"

    id = Column(Integer, primary_key=True, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    transaction = relationship(Transaction, backref="subtransactions")
   
    quantity = Column(Integer, nullable=False) 
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    item = relationship(Item, backref="subtransactions")
    amount = Column(Float, nullable=False)
    
    def __init__(self, transaction, item, quantity):
        self.item_id = item.id
        self.quantity = quantity
        self.amount = quantity * amount


def purchase(user_id, items={}):
    user = DBSession.query(User).filter(User.id == int(user_id)).one()
    t = Transaction
