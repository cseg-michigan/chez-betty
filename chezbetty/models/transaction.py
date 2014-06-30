from .model import *
from .account import Account, make_account
from .item import Item

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)
    to_account_id = Column(Integer, ForeignKey("accounts.id"))
    from_account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(Float, nullable=False)
    notes = Column(Text)
    type = Column(Enum("purchase", "deposit", "reconciliation", 
            "adjustment", "restock", "btcdeposit", name="transaction_type"), nullable=False)
    __mapper_args__ = {'polymorphic_on':type}
    # user that performed the reconciliation 
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
   
    to_account = relationship(Account, 
        foreign_keys=[to_account_id,],
        backref="transactions_to"
    )
    
    from_account = relationship(Account, 
        foreign_keys=[from_account_id,],
        backref="transactions_from"
    )

    def __init__(self, from_account, to_account, amount):
        self.to_account_id = to_account.id if to_account else None
        self.from_account_id = from_account.id if from_account else None
        self.amount = amount
        if to_account:
            to_account.balance += self.amount
        if from_account:
            from_account.balance -= self.amount

    def update_amount(self, amount):
        if self.to_account:
            self.to_account.balance -= self.amount
        if self.from_account:
            self.from_account.balance += self.amount
        self.amount = amount
        if self.to_account:
            self.to_account.balance += self.amount
        if self.from_account:
            self.from_account.balance -= self.amount

    @classmethod
    def from_id(cls, id):
        t = DBSession.query(cls).filter(cls.id == id).one()
        return t

@property
def __transactions(self):
    return object_session(self).query(Transaction)\
            .filter(or_(
                    Transaction.to_account_id == self.id,
                    Transaction.from_account_id == self.id)).all()
Account.transactions = __transactions


class Deposit(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'deposit'}

    def __init__(self, user, amount):
        Transaction.__init__(self, None, user, amount)


class BTCDeposit(Deposit):
    __mapper_args__ = {'polymorphic_identity': 'btcdeposit'}
   
    btctransaction = Column(String(64))
    address = Column(String(64))
    amount_btc = Column(Float, nullable=False)

    def __init__(self, user, amount, btctransaction, address, amount_btc):
        Transaction.__init__(self, None, user, amount)
        self.btctransaction = btctransaction
        self.address = address
        self.amount_btc = amount_btc


class Purchase(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'purchase'}
    def __init__(self, user):
        chezbetty = make_account("chezbetty")
        Transaction.__init__(self, user, chezbetty, 0.0)


class Restock(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'restock'}
    def __init__(self, user):
        chezbetty = make_account("chezbetty")
        store = make_account("store")
        Transaction.__init__(self, chezbetty, store, 0.0)


class Reconciliation(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'reconciliation'}
        
    def __init__(self, user):
        chezbetty = make_account("chezbetty")
        lost = make_account("lost")
        Transaction.__init__(self, chezbetty, lost, 0.0)
        self.user_id = user.id if user else None


class Adjustment(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'adjustment'}

    def __init__(self, user, amount, admin, notes):
        chezbetty = make_account("chezbetty")
        Transaction.__init__(self, chezbetty, user, amount)
        self.user_id = admin.id if admin else None
        self.notes = notes


class SubTransaction(Base):
    __tablename__ = "subtransactions"

    id = Column(Integer, primary_key=True, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    transaction = relationship(Transaction, backref="subtransactions", cascade="all")
   
    quantity = Column(Integer, nullable=False) 
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    item = relationship(Item, backref="subtransactions")
    amount = Column(Float, nullable=False)
    
    def __init__(self, transaction, item, quantity, amount):
        self.transaction_id = transaction.id
        self.item_id = item.id
        self.quantity = quantity
        self.amount = quantity * amount

    @property
    def item_amount(self):
       return self.amount/self.quantity
