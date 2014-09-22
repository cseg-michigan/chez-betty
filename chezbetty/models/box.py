from .model import *

class Box(Base):
    __tablename__ = 'boxes'

    id         = Column(Integer, primary_key=True, nullable=False)
    name       = Column(String(255), nullable=False, unique=True)
    barcode    = Column(String(255), nullable=True, unique=True)
    wholesale  = Column(Numeric, nullable=False)
    bottle_dep = Column(Boolean, nullable=False, default=False)
    sales_tax  = Column(Boolean, nullable=False, default=False)

    enabled    = Column(Boolean, default=True, nullable=False)

    def __init__(self, name, barcode, bottle_dep,
                 sales_tax, wholesale=0, enabled=True):
        self.name = name
        self.barcode = barcode
        self.wholesale = wholesale
        self.bottle_dep = bottle_dep
        self.sales_tax = sales_tax
        self.enabled = enabled

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def from_barcode(cls, barcode):
        return DBSession.query(cls).filter(cls.barcode == barcode).one()

    @classmethod
    def from_fuzzy(cls, search_str):
        return DBSession.query(cls)\
                        .filter(or_(
                            cls.barcode.ilike('%{}%'.format(search_str)),
                            cls.name.ilike('%{}%'.format(search_str))
                        )).all()

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
