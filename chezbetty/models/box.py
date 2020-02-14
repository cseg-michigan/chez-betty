from .model import *
import re

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
        box_list = DBSession.query(cls).filter(cls.barcode.ilike('%{}%'.format(barcode))).all()
        if(len(box_list) == 1):
            return box_list[0]
        else: #list length other than 1 is likely a bad scan, so search for exact match to throw exception if needed
            return DBSession.query(cls).filter(cls.barcode == barcode).one()
        #TODO: handle the two cases where len(box_list) != 1 (len is 0, len is > 1)

    @classmethod #search for all delimited barcodes in database; return true if any matches are found
    def update_exists_barcode(cls, barcode, id):
        sub = re.compile(r'[^\d;]+').sub('', barcode).split(';') #remove any characters that aren't digits or delimiters
        result = False
        for single_barcode in sub:
            if single_barcode is not "":
                result = DBSession.query(func.count(cls.id).label('c'))\
                            .filter(cls.id != id)\
                            .filter(cls.barcode.ilike('%{}%'.format(single_barcode))).one().c > 0
                if(result):
                    return result
        return result

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
