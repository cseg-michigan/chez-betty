from .model import *

class Request(Base):
    __tablename__ = 'requests'

    id        = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=True) # user that made the request
    request   = Column(Text)
    enabled   = Column(Boolean, default=True, nullable=False)
    deleted   = Column(Boolean, default=False, nullable=False)

    def __init__(self, user, request):
        if user:
            self.user_id = user.id
        self.request = request

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls).filter(cls.deleted==False).all()

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.enabled)\
                        .filter(cls.deleted==False).one().c
