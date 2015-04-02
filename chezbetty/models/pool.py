import os
from .model import *
from . import account
from chezbetty import utility


class Pool(account.Account):
    __tablename__ = 'pools'
    __mapper_args__ = {'polymorphic_identity': 'pool'}

    id           = Column(Integer, ForeignKey("accounts.id"), primary_key=True)
    owner        = Column(Integer, ForeignKey("users.id"), primary_key=True)
    credit_limit = Column(Numeric, nullable=False, default=20)
    enabled      = Column(Boolean, nullable=False, default=True)

    def __init__(self, owner, name):
        self.owner = owner.id
        self.name = name
        self.balance = 0.0

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()
        return u

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .order_by(cls.name)\
                        .all()

    @classmethod
    def all_by_owner(cls, user, only_enabled=False):
        q = DBSession.query(cls).filter(cls.owner==user.id)
        if only_enabled:
            q.filter(cls.enabled==True)
        return q.all()

    @classmethod
    def all_accessable(cls, user, only_enabled=False):
        # Get all pools the user can access
        pools = []
        for pool in Pool.all_by_owner(user, only_enabled):
            if not only_enabled or pool.enabled:
                pools.append(pool)

        for pu in user.pools:
            if not only_enabled or pu.pool.enabled:
                pools.append(pu.pool)

        return pools

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.enabled==True)\
                        .one().c
