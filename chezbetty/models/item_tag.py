from .model import *
from . import tag
from . import item

class ItemTag(Base):
    __tablename__ = 'item_tags'

    id      = Column(Integer, primary_key=True, nullable=False)
    tag_id  = Column(Integer, ForeignKey('tags.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)

    deleted = Column(Boolean, default=False, nullable=False)

    tag     = relationship(tag.Tag,
                           primaryjoin='and_(ItemTag.tag_id==tag.Tag.id, ItemTag.deleted==False)',
                           backref='items')
    item    = relationship(item.Item,
                           primaryjoin='and_(ItemTag.item_id==item.Item.id, ItemTag.deleted==False)',
                           backref='tags')

    def __init__(self, item, tag):
        self.tag_id  = tag.id
        self.item_id = item.id

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

@classmethod
@limitable_all
def __get_tags_with_nobarcode_items(cls):
    return DBSession.query(tag.Tag)\
            .join(ItemTag)\
            .join(item.Item)\
            .filter(item.Item.barcode == None)\
            .filter(ItemTag.deleted==False)\
            .filter(item.Item.enabled==True)\
            .filter(tag.Tag.deleted==False)

tag.Tag.get_tags_with_nobarcode_items = __get_tags_with_nobarcode_items

@property
@limitable_all
def __nobarcode_items(self):
    return DBSession.query(item.Item)\
            .join(ItemTag)\
            .join(tag.Tag)\
            .filter(ItemTag.tag_id == self.id)\
            .filter(item.Item.barcode == None)\
            .filter(ItemTag.deleted==False)\
            .filter(item.Item.enabled==True)\
            .filter(tag.Tag.deleted==False)

tag.Tag.nobarcode_items = __nobarcode_items

@property
@limitable_all
def __all_items(self):
    return DBSession.query(item.Item)\
            .join(ItemTag)\
            .join(tag.Tag)\
            .filter(ItemTag.tag_id == self.id)\
            .filter(ItemTag.deleted==False)\
            .filter(tag.Tag.deleted==False)\
            .order_by(item.Item.name)

tag.Tag.all_items = __all_items

@property
@limitable_all
def __all_enabled_items(self):
    return DBSession.query(item.Item)\
            .join(ItemTag)\
            .join(tag.Tag)\
            .filter(ItemTag.tag_id == self.id)\
            .filter(ItemTag.deleted==False)\
            .filter(item.Item.enabled==True)\
            .filter(tag.Tag.deleted==False)\
            .order_by(item.Item.name)

tag.Tag.all_enabled_items = __all_enabled_items

@classmethod
@limitable_all
def __get_nobarcode_notag_items(cls):
    return DBSession.query(item.Item)\
            .filter(item.Item.barcode == None)\
            .filter(item.Item.enabled == True)\
            .filter(~exists().where(
                 and_(ItemTag.item_id == item.Item.id,
                      ItemTag.deleted == False)))

item.Item.get_nobarcode_notag_items = __get_nobarcode_notag_items

