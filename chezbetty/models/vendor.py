from .model import *

class Vendor(Base):
    __tablename__ = 'vendors'

    id        = Column(Integer, primary_key=True, nullable=False)
    name      = Column(String(255), nullable=False)

    enabled   = Column(Boolean, default=True, nullable=False)

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

    def __str__(self):
        return "<Vendor (%s)>" % self.name

    __repr__ = __str__
