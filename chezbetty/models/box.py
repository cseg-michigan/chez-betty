from .model import *

class Box(Base):
    __tablename__ = 'boxes'

    id        = Column(Integer, primary_key=True, nullable=False)
    name      = Column(String(255), nullable=False, unique=True)
    barcode   = Column(String(255), nullable=True, unique=True)
    wholesale = Column(Numeric, nullable=False)

    enabled   = Column(Boolean, default=True, nullable=False)

    def __init__(self, name, barcode, wholesale=0, enabled=True):
        self.name = name
        self.barcode = barcode
        self.enabled = enabled
        self.wholesale = wholesale

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def from_barcode(cls, barcode):
        return DBSession.query(cls).filter(cls.barcode == barcode).one()

    @classmethod
    def from_barcode_fuzzy(cls, barcode):
        return DBSession.query(cls).filter(cls.barcode.like('%{}%'.format(barcode))).all()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .order_by(cls.name).all()

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.enabled).one().c

    @classmethod
    def get_enabled(cls):
        return cls.all()

    @classmethod
    def get_disabled(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled==False)\
                        .order_by(cls.name).all()

    @classmethod
    def exists_name(cls, name):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.name == name).one().c > 0

    @classmethod
    def exists_barcode(cls, barcode):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.barcode == barcode).one().c > 0

    def __str__(self):
        return '<Box ({})>'.format(self.name)

    __repr__ = __str__
