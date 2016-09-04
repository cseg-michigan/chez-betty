from .model import *
from . import account


class Reimbursee(account.Account):
    __tablename__ = 'reimbursees'
    __mapper_args__ = {'polymorphic_identity': 'reimbursee'}

    id        = Column(Integer, ForeignKey("accounts.id"), primary_key=True)
    enabled   = Column(Boolean, nullable=False, default=True)

    def __init__(self, name):
        self.enabled = True
        self.name = name
        self.balance = 0.0

    def __str__(self):
        return "<Reimbursee: id {}, name {}, balance {}>".\
                format(self.id, self.name, self.balance)

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .order_by(cls.name)\
                        .all()

    @classmethod
    def get_owed(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .filter(cls.balance != 0)\
                        .order_by(cls.name)\
                        .all()

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.enabled == True)\
                        .one().c

    @classmethod
    def get_outstanding_reimbursements_total(cls):
        return DBSession.query(func.sum(Reimbursee.balance).label("total_balance"))\
                        .one().total_balance or Decimal(0.0)
