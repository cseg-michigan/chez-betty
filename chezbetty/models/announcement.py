from .model import *

from sqlalchemy_utils import ArrowType

class Announcement(Base):
    __tablename__ = 'announcements'

    id           = Column(Integer, primary_key=True, nullable=False)
    timestamp    = Column(ArrowType, nullable=False, default=datetime.datetime.utcnow)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False) # user that added the announcement
    announcement = Column(Text)
    enabled      = Column(Boolean, default=True, nullable=False)
    deleted      = Column(Boolean, default=False, nullable=False)

    def __init__(self, user, announcement):
        self.user_id = user.id
        self.announcement = announcement

    @classmethod
    def from_id(cls, id):
        e = DBSession.query(cls).filter(cls.id == id).one()
        return e

    @classmethod
    def all(cls):
        e = DBSession.query(cls).filter(cls.deleted==False).all()
        return e

    @classmethod
    def all_enabled(cls):
        e = DBSession.query(cls)\
                     .filter(cls.deleted==False)\
                     .filter(cls.enabled==True)\
                     .all()
        return e
