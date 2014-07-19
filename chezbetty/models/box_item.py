from .model import *
from . import box
from . import item

class BoxItem(Base):
    __tablename__ = 'box_items'

    id          = Column(Integer, primary_key=True, nullable=False)
    box_id      = Column(Integer, ForeignKey("boxes.id"), nullable=False)
    item_id     = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity    = Column(Integer, nullable=False)

    enabled     = Column(Boolean, default=True, nullable=False)

    box         = relationship(box.Box, foreign_keys=[box_id,], backref="items")
    item        = relationship(item.Item, foreign_keys=[item_id,], backref="boxes")

    def __init__(self, box, item, quantity, enabled=True):
        self.box_id   = box.id
        self.item_id  = item.id
        self.quantity = quantity
        self.enabled  = enabled

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()
