from .model import *

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(Enum("client", "special"), nullable=False)
    balance = Column(Float, nullable=False)
    name = Column(String(255), nullable=False)


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)
    amount = Column(Float, nullable=False)

    @validates("amount")
    def __validate_amount(self, key, amount):
        assert(amount > 0.0)
        return amount

    to_account = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    from_account = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    type = Column(Enum("purchase",), nullable=False)
    __mapper_args__ = {'polymorphic_on':type}
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now)


class Purchase(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'purchase'}
    pass


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


# special accounts
chezbetty = DBSession.query(Account).filter(Account.name == "chezbetty").one()
storage   = DBSession.query(Account).filter(Account.name == "storage").one()
lost      = DBSession.query(Account).filter(Account.name == "lost").one()
bank      = DBSession.query(Account).filter(Account.name == "chezbetty").one()
desposit  = DBSession.query(Account).filter(Account.name == "chezbetty").one()


def purchase(user_id, items={}):
    user = DBSession.query(User).filter(User.id == int(user_id)).one()
    t = Transaction
