from .model import *
from . import tag as tagobject

class TagRelations(Base):
    __tablename__ = 'tag_relations'

    id            = Column(Integer, primary_key=True, nullable=False)
    tag_id        = Column(Integer, ForeignKey('tags.id'), nullable=False)
    parent_tag_id = Column(Integer, ForeignKey('tags.id'), nullable=False)

    deleted       = Column(Boolean, default=False, nullable=False)

    tag           = relationship(tagobject.Tag,
                                 primaryjoin=tag_id==tagobject.Tag.id,
                                 backref='parents')

    parent        = relationship(tagobject.Tag,
                                 primaryjoin=parent_tag_id==tagobject.Tag.id,
                                 backref='children')


    def __init__(self, tag, parent_tag):
        self.tag_id        = tag.id
        self.parent_tag_id = parent_tag.id
