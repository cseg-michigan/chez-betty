from .model import *
from . import tag
from . import item

class ItemTag(Base):
    __tablename__ = 'item_tags'

    id      = Column(Integer, primary_key=True, nullable=False)
    tag_id  = Column(Integer, ForeignKey('tags.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)

    deleted = Column(Boolean, default=False, nullable=False)

    tag     = relationship(tag.Tag, backref='items')
    item    = relationship(item.Item, backref='tags')

    def __init__(self, item, tag):
        self.tag_id  = tag.id
        self.item_id = item.id
