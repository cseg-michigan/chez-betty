from .model import *
from . import account
from . import user
from . import pool

class PoolUser(Base):
    __tablename__ = 'pool_users'

    id          = Column(Integer, primary_key=True, nullable=False)
    pool_id     = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)

    enabled     = Column(Boolean, default=True, nullable=False)
    deleted     = Column(Boolean, default=False, nullable=False)

    pool        = relationship(
                    account.Account,
                    primaryjoin="and_(PoolUser.pool_id==Account.id, PoolUser.deleted==False)",
                    backref="users"
                  )
    user        = relationship(
                    user.User,
                    primaryjoin="and_(PoolUser.user_id==User.id, PoolUser.deleted==False)",
                    backref="pools"
                  )

    def __init__(self, pool, user):
        self.pool_id  = pool.id
        self.user_id  = user.id

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()
