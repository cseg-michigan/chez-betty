from .model import *
from . import vendor
from . import item

class ItemVendor(Base):
    __tablename__ = 'item_vendors'

    id          = Column(Integer, primary_key=True, nullable=False)
    vendor_id   = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    item_id     = Column(Integer, ForeignKey("items.id"), nullable=False)
    item_number = Column(String(255), nullable=False)

    enabled     = Column(Boolean, default=True, nullable=False)

    vendor      = relationship(vendor.Vendor, foreign_keys=[vendor_id,], backref="items")
    item        = relationship(item.Item, foreign_keys=[item_id,], backref="vendors")

    def __init__(self, vendor, item, item_number, enabled=True):
        self.vendor_id   = vendor.id
        self.item_id     = item.id
        self.item_number = item_number
        self.enabled     = enabled

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()
