from .model import *

class Vendor(Base):
    __tablename__ = 'vendors'

    id           = Column(Integer, primary_key=True, nullable=False)
    name         = Column(String(255), nullable=False)

    enabled      = Column(Boolean, default=True, nullable=False)
    product_urls = Column(Boolean)

    def __init__(self, name, enabled=True):
        self.name = name
        self.enabled = enabled

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .order_by(cls.name).all()

    @classmethod
    def disabled(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled==False)\
                        .order_by(cls.name).all()

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.enabled).one().c

    def __str__(self):
        return "<Vendor (%s)>" % self.name

    __repr__ = __str__
