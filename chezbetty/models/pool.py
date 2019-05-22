import os
from .model import *
from .user import User
from . import account
from chezbetty import utility


class Pool(account.Account):
    __tablename__ = 'pools'
    __mapper_args__ = {'polymorphic_identity': 'pool'}

    id           = Column(Integer, ForeignKey("accounts.id"), primary_key=True)
    owner        = Column(Integer, ForeignKey("users.id"), primary_key=True)
    credit_limit = Column(Numeric, nullable=False, default=0)
    enabled      = Column(Boolean, nullable=False, default=True)

    def __init__(self, owner, name):
        self.owner = owner.id
        self.name = name
        self.balance = 0.0

    def get_owner_name(self):
        return User.from_id(self.owner).name

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()
        return u

    @classmethod
    def from_fuzzy(cls, search_str, any=True):
        q = DBSession.query(cls)\
                     .filter(cls.name.ilike('%{}%'.format(search_str)))
        if not any:
            q = q.filter(cls.enabled)

        return q.all()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled==True)\
                        .order_by(cls.name)\
                        .all()

    @classmethod
    def disabled(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled==False)\
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

    # Sum the total amount of money in user accounts that we are holding for
    # pools. This is different from just getting the total because it doesn't
    # count pools with negative balances
    @classmethod
    def get_amount_held(cls):
        return DBSession.query(func.sum(Pool.balance).label("total_balance"))\
                        .filter(Pool.balance>0)\
                        .one().total_balance or Decimal(0.0)

    @classmethod
    def get_amount_owed(cls):
        return DBSession.query(func.sum(Pool.balance).label("total_balance"))\
                        .filter(Pool.balance<0)\
                        .one().total_balance or Decimal(0.0)
