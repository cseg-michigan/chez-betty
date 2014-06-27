from .model import *

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(Enum("client", "special"), nullable=False)
    balance = Column(Float, nullable=False)
    name = Column(String(255), nullable=False)


# special accounts
chezbetty = DBSession.query(Account).filter(Account.name == "chezbetty").one()
lost      = DBSession.query(Account).filter(Account.name == "lost").one()

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)
    amount = Column(Float, nullable=False)

    @validates("amount")
    def __validate_amount(self, key, amount):
        assert(amount > 0.0)
        return amount

    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    to_account = relation(Account, )

    type = Column(Enum("purchase",), nullable=False)
    __mapper_args__ = {'polymorphic_on':type}
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)


class Purchase(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'purchase'}
    def __init__(self, user):
        from_account = user
        to_account = chezbetty


class Inventory(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'inventory'}
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class Restock(Transaction):
    pass



class SubTransaction(Base):
    __tablename__ = "subtransactions"

    id = Column(Integer, primary_key=True, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
   
    count = Column(Integer, nullable=False) 
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    amount = Column(Float, nullable=False)
    
    def __init__(self, transaction, item, quantity):
        pass


def purchase(user_id, items={}):
    user = DBSession.query(User).filter(User.id == int(user_id)).one()
    t = Transaction
