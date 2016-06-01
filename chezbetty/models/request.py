from .model import *
from . import vendor
from . import request_post

from sqlalchemy_utils import ArrowType

class Request(Base):
    __tablename__ = 'requests'

    id         = Column(Integer, primary_key=True, nullable=False)
    timestamp  = Column(ArrowType, nullable=False, default=datetime.datetime.utcnow)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    request    = Column(Text)
    vendor_id  = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    vendor_url = Column(Text)
    enabled    = Column(Boolean, default=True, nullable=False)
    deleted    = Column(Boolean, default=False, nullable=False)

    vendor     = relationship(
                    vendor.Vendor,
                    primaryjoin="and_(Request.vendor_id==Vendor.id, Request.deleted==False)",
                    backref="requests",
                  )

    posts      = relationship(
                   request_post.RequestPost,
                   primaryjoin="and_(RequestPost.request_id==Request.id, RequestPost.deleted==False)",
                   backref="request",
                 )
    deleted_posts = relationship(
                   request_post.RequestPost,
                   primaryjoin="and_(RequestPost.request_id==Request.id, RequestPost.deleted==True)",
                 )
    all_posts  = relationship(
                   request_post.RequestPost,
                   primaryjoin="RequestPost.request_id==Request.id",
                 )

    def __init__(self, user, request, vendor, vendor_url=None):
        self.user_id = user.id
        self.request = request
        self.vendor_id = vendor.id
        if vendor_url:
            self.vendor_url = vendor_url

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls).filter(cls.deleted==False)\
                        .order_by(desc(cls.timestamp))\
                        .all()

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.enabled)\
                        .filter(cls.deleted==False).one().c
