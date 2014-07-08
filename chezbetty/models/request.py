from .model import *

class Request(Base):
    __tablename__ = 'requests'

    id        = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=True) # user that made the request
    request   = Column(Text)
    enabled   = Column(Boolean, default=True, nullable=False)

    def __init__(self, user, request):
        if user:
            self.user_id = user.id
        self.request = request

    @classmethod
    def from_id(cls, id):
        e = DBSession.query(cls).filter(cls.id == id).one()
        return e

    @classmethod
    def all(cls):
        e = DBSession.query(cls).filter(cls.enabled).all()
        return e
