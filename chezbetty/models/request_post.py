from .model import *

from sqlalchemy_utils import ArrowType

class RequestPost(Base):
    __tablename__ = 'request_posts'

    id         = Column(Integer, primary_key=True, nullable=False)
    timestamp  = Column(ArrowType, nullable=False, default=datetime.datetime.utcnow)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    post       = Column(Text)
    # Allow admin users to post as users or admins by tracking the view that the post is posted from
    staff_post = Column(Boolean, default=False, nullable=False)
    deleted    = Column(Boolean, default=False, nullable=False)

    def __init__(self, request, user, post, staff_post=False, deleted=False):
        self.request_id = request.id
        self.user_id = user.id
        self.post = post
        self.staff_post = staff_post
        self.deleted = deleted

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls).filter(cls.deleted==False)\
                        .order_by(desc(cls.timestamp))\
                        .all()

