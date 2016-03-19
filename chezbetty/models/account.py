from .model import *

from sqlalchemy_utils import ArrowType

class Account(Versioned, Base):
    __tablename__ = "accounts"

    id               = Column(Integer, primary_key=True, nullable=False)
    type             = Column(Enum("user", "virtual", "cash", "pool", name="account_type"), nullable=False)
    name             = Column(String(255), nullable=False)
    balance          = Column(Numeric, nullable=False)
    archived_balance = Column(Numeric, nullable=True)
    created_at       = Column(ArrowType, default=datetime.datetime.utcnow)

    __mapper_args__ = {'polymorphic_on': type}

    def __init__(self, name):
        self.name = name
        self.balance = Decimal(0.0)

    @classmethod
    def from_name(cls, name):
        return DBSession.query(cls).filter(cls.name == name).one()


class VirtualAccount(Account):
    __mapper_args__ = {'polymorphic_identity': 'virtual'}


class CashAccount(Account):
    __mapper_args__ = {'polymorphic_identity': 'cash'}


# Get an account object of the virtual account corresponding to the argument
# "name". If one does not exist, make it transparently.
def get_virt_account(name):
    t = DBSession.query(VirtualAccount).filter(VirtualAccount.name == name).first()
    if t:
        return t
    t = VirtualAccount(name)
    DBSession.add(t)
    DBSession.flush()
    return t

def get_cash_account(name):
    t = DBSession.query(CashAccount).filter(CashAccount.name == name).first()
    if t:
        return t
    t = CashAccount(name)
    DBSession.add(t)
    DBSession.flush()
    return t
