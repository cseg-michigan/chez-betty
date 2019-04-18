from .model import *
import re

class ItemImage(Base):
    __tablename__ = 'items_images'

    id         = Column(Integer, primary_key=True, nullable=False)
    item_id    = Column(Integer, ForeignKey("items.id"), nullable=False)
    img        = Column(LargeBinary, nullable=False)

    def __init__(self, item_id, img):
        self.item_id = item_id
        self.img = img

    def __str__(self):
        return "<ItemImage (%s)>" % self.item.name

    __repr__ = __str__


class Item(Versioned, Base):
    __tablename__ = 'items'

    id           = Column(Integer, primary_key=True, nullable=False)
    name         = Column(String(255), nullable=False, unique=True)
    barcode      = Column(String(255), nullable=True, unique=True)
    price        = Column(Numeric, nullable=False)
    sticky_price = Column(Boolean, default=False)
    wholesale    = Column(Numeric, nullable=False)
    bottle_dep   = Column(Boolean, nullable=False, default=False)
    sales_tax    = Column(Boolean, nullable=False, default=False)
    in_stock     = Column(Integer, nullable=False, default=0)
    img          = relationship(ItemImage, uselist=False, backref="item")

    enabled      = Column(Boolean, default=True, nullable=False)

    def __init__(self, name, barcode, price, wholesale, bottle_dep, sales_tax,
                 in_stock, enabled):
        self.name = name
        self.barcode = re.compile(r'[^\d;]+').sub('', barcode) #remove any characters that aren't digits or delimiters
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
    def from_barcode_sub(cls, barcode):
        item_list = DBSession.query(cls).filter(cls.barcode.ilike('%{}%'.format(barcode))).all()
        if(len(item_list) == 1):
            return item_list[0]
        else: #list length other than 1 is likely a bad scan, so search for exact match to throw exception if needed
            return DBSession.query(cls).filter(cls.barcode == barcode).one()
        #TODO: handle the two cases where len(item_list) != 1 (len is 0, len is > 1)


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
    def disabled(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled==False)\
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

    @classmethod #search for all delimited barcodes in database; return true if any matches are found
    def exists_barcode_sub(cls, barcode):
        sub = re.compile(r'[^\d;]+').sub('', barcode).split(';') #remove any characters that aren't digits or delimiters
        result = False
        for single_barcode in sub:
            result = DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.barcode.ilike('%{}%'.format(single_barcode))).one().c > 0
            if(result):
                return result
        return result

    @classmethod
    def total_inventory_wholesale(cls):
        return DBSession.query(func.sum(cls.wholesale * cls.in_stock).label('c'))\
                        .one().c or 0

    def __str__(self):
        return "<Item (%s)>" % self.name

    __repr__ = __str__
    