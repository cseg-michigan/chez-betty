from model import *

class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    barcode = Column(String(255), nullable=True)
    price = Column(Float, nullable=True)
    
    enabled = Column(Boolean, default=True, nullable=False)
    in_stock = Column(Integer, nullable=False, default=0)