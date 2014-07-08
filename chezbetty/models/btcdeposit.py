from .model import *
from . import account
from . import item

class BtcPendingDeposit(Base):
    __tablename__ = 'btcpending'

    id        = Column(Integer, primary_key=True, nullable=False)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False) # user the address "belongs" to
    auth_key  = Column(String(64), nullable=False)  # authentication string needed in the callback, otherwise it probably didn't come from coinbase
    address   = Column(String(64), nullable=False)  # bitcoin address

    def __init__(self, user, auth_key, address):
        self.user_id = user.id
        self.auth_key = auth_key
        self.address = address

    @classmethod
    def from_id(cls, id):
        e = DBSession.query(cls).filter(cls.id == id).one()
        return e

    @classmethod
    def from_auth_key(cls, auth_key):
        e = DBSession.query(cls).filter(cls.auth_key == auth_key).one()
        return e
