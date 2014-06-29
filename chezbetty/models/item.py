from .model import *

class Item(Versioned, Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    barcode = Column(String(255), nullable=True)
    price = Column(Float, nullable=False)
    wholesale = Column(Float, nullable=False)

    enabled = Column(Boolean, default=True, nullable=False)
    in_stock = Column(Integer, nullable=False, default=0)

    def __init__(self, name, barcode, price, wholesale, in_stock, enabled):
        self.name = name
        self.barcode = barcode
        self.price = price
        self.wholesale = wholesale
        self.in_stock = in_stock
        self.enabled = enabled

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def from_barcode(cls, barcode):
        return DBSession.query(cls).filter(cls.barcode == barcode).one()
