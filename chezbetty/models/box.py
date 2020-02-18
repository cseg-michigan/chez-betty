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
        for box in box_list:
            #split string into individual barcodes
            box_barcode_sub = box.barcode.split(';')
            #check each barcode for an EXACT match
            for single_box_barcode_sub in box_barcode_sub:
                if single_box_barcode_sub == barcode:
                    return box
        #if we get here it is likely a bad scan, so search for exact match to throw exception if needed
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

    @classmethod #search for all delimited barcodes in database; return true if any matches are found
    def exists_barcode(cls, barcode, id=None):
        #split string into individual barcodes
        barcode_list = barcode.split(';')
        for single_barcode in barcode_list:
            if single_barcode != "":
                #retreive the list (if any) of boxes containing this barcode; required due to substring matches
                box_list = DBSession.query(cls).filter(cls.id != id).filter(cls.barcode.ilike('%{}%'.format(single_barcode))).all()
                for box in box_list:
                    #split string into individual barcodes
                    box_barcode_list = box.barcode.split(';')
                    #check each barcode for an EXACT match
                    for single_box_barcode_sub in box_barcode_list:
                        if single_box_barcode_sub == single_barcode:
                            return True
        return False

    def __str__(self):
        return '<Box ({})>'.format(self.name)

    __repr__ = __str__
