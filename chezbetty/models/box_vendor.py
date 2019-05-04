from .model import *
from . import vendor
from . import box

class BoxVendor(Base):
    __tablename__ = 'box_vendors'

    id          = Column(Integer, primary_key=True, nullable=False)
    vendor_id   = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    box_id      = Column(Integer, ForeignKey("boxes.id"), nullable=False)
    item_number = Column(String(255), nullable=False)

    enabled     = Column(Boolean, default=True, nullable=False)

    vendor      = relationship(
                      vendor.Vendor,
                      primaryjoin="and_(BoxVendor.vendor_id==Vendor.id, BoxVendor.enabled==True)",
                      backref="boxes"
                  )
    box         = relationship(
                      box.Box,
                      primaryjoin="and_(BoxVendor.box_id==Box.id, BoxVendor.enabled==True)",
                      backref="vendors"
                  )


    def __init__(self, vendor, box, item_number, enabled=True):
        self.vendor_id   = vendor.id
        self.box_id      = box.id
        self.item_number = item_number
        self.enabled     = enabled

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def from_number_fuzzy(cls, number):
        return DBSession.query(cls).filter(cls.item_number.like('%{}%'.format(number))).all()

@property
def __all_boxes(self):
    return DBSession.query(box.Box)\
            .join(BoxVendor)\
            .filter(BoxVendor.vendor_id == self.id)\
            .filter(BoxVendor.enabled==True)\
            .filter(box.Box.enabled==True)\
            .order_by(box.Box.name)
vendor.Vendor.all_boxes = __all_boxes
