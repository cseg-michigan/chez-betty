import os
from .model import *
from . import account
from chezbetty import utility


class Pool(account.Account):
    __tablename__ = 'pools'
    __mapper_args__ = {'polymorphic_identity': 'pool'}

    id        = Column(Integer, ForeignKey("accounts.id"), primary_key=True)
    owner     = Column(Integer, ForeignKey("users.id"), primary_key=True)
    enabled   = Column(Boolean, nullable=False, default=True)

    def __init__(self, owner):
        self.owner = owner.id
        self.balance = 0.0

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()
        return u

    @classmethod
    def all(cls):
        return DBSession.query(cls).filter(cls.enabled).all()

    @classmethod
    def all_by_owner(cls, user):
        return DBSession.query(cls).filter(cls.owner==user.id)

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c')).one().c
