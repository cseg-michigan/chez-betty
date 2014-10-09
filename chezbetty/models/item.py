from .model import *

class Item(Versioned, Base):
    __tablename__ = 'items'

    id         = Column(Integer, primary_key=True, nullable=False)
    name       = Column(String(255), nullable=False, unique=True)
    barcode    = Column(String(255), nullable=True, unique=True)
    price      = Column(Numeric, nullable=False)
    wholesale  = Column(Numeric, nullable=False)
    bottle_dep = Column(Boolean, nullable=False, default=False)
    sales_tax  = Column(Boolean, nullable=False, default=False)
    in_stock   = Column(Integer, nullable=False, default=0)

    enabled    = Column(Boolean, default=True, nullable=False)

    def __init__(self, name, barcode, price, wholesale, bottle_dep, sales_tax,
                 in_stock, enabled):
        self.name = name
        self.barcode = barcode
        self.price = price
        self.wholesale = wholesale
        self.bottle_dep = bottle_dep
        self.sales_tax = sales_tax
        self.in_stock = in_stock
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
    def from_name(cls, name):
        return DBSession.query(cls).filter(cls.name == name).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .order_by(cls.name).all()

    @classmethod
    def all_force(cls):
        return DBSession.query(cls)\
                        .order_by(cls.name).all()

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.enabled).one().c

    @classmethod
    def exists_name(cls, name):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.name == name).one().c > 0

    @classmethod
    def exists_barcode(cls, barcode):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.barcode == barcode).one().c > 0

    @classmethod
    def total_inventory_wholesale(cls):
        return DBSession.query(func.sum(cls.wholesale * cls.in_stock).label('c'))\
                        .one().c or 0

    def __str__(self):
        return "<Item (%s)>" % self.name

    __repr__ = __str__
