from .model import *
from . import box
from . import item

class BoxItem(Base):
    __tablename__ = 'box_items'

    id          = Column(Integer, primary_key=True, nullable=False)
    box_id      = Column(Integer, ForeignKey("boxes.id"), nullable=False)
    item_id     = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity    = Column(Integer, nullable=False)
    percentage  = Column(Numeric, nullable=False)

    enabled     = Column(Boolean, default=True, nullable=False)

    box         = relationship(
                    box.Box,
                    primaryjoin="and_(BoxItem.box_id==Box.id, BoxItem.enabled==True)",
                    backref="items"
                  )
    item        = relationship(
                    item.Item,
                    primaryjoin="and_(BoxItem.item_id==Item.id, BoxItem.enabled==True)",
                    backref="boxes"
                  )

    def __init__(self, box, item, quantity, percentage, enabled=True):
        self.box_id     = box.id
        self.item_id    = item.id
        self.quantity   = quantity
        self.percentage = percentage
        self.enabled    = enabled

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

@property
def __subitem_quantity(self):
    return object_session(self).query(func.sum(BoxItem.quantity).label('c'))\
            .filter(BoxItem.box_id==self.id)\
            .filter(BoxItem.enabled).one().c or 0
box.Box.subitem_count = __subitem_quantity

@property
def __subitem_count(self):
    return object_session(self).query(func.count(BoxItem.id).label('c'))\
            .filter(BoxItem.box_id==self.id)\
            .filter(BoxItem.enabled).one().c or 0
box.Box.subitem_number = __subitem_count

@property
def __subitem_active_count(self):
    return object_session(self).query(func.count(BoxItem.id).label('c'))\
            .join(item.Item)\
            .filter(BoxItem.box_id==self.id)\
            .filter(BoxItem.enabled)\
            .filter(item.Item.enabled)\
            .one().c or 0
box.Box.subitem_active_number = __subitem_active_count

@property
def __all_items(self):
    return DBSession.query(item.Item)\
            .join(BoxItem)\
            .filter(BoxItem.box_id == self.id)\
            .filter(BoxItem.enabled==True)\
            .order_by(item.Item.name)
box.Box.all_items = __all_items
