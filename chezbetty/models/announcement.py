from .model import *

class Announcement(Base):
    __tablename__ = 'announcements'

    id           = Column(Integer, primary_key=True, nullable=False)
    timestamp    = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False) # user that added the announcement
    announcement = Column(Text)
    enabled      = Column(Boolean, default=True, nullable=False)

    def __init__(self, user, announcement):
        self.user_id = user.id
        self.announcement = announcement

    @classmethod
    def from_id(cls, id):
        e = DBSession.query(cls).filter(cls.id == id).one()
        return e

    @classmethod
    def all(cls):
        e = DBSession.query(cls).filter(cls.enabled).all()
        return e
