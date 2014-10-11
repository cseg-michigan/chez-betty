from .model import *

class Tag(Base):
    __tablename__ = 'tags'

    id         = Column(Integer, primary_key=True, nullable=False)
    name       = Column(String(255), nullable=False, unique=True)

    # Show this page as a top-level item selector
    homepage   = Column(Boolean, nullable=False, default=False)

    enabled    = Column(Boolean, default=True, nullable=False)
    deleted    = Column(Boolean, default=False, nullable=False)

    def __init__(self, name):
        self.name = name

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.deleted==False)\
                        .order_by(cls.name).all()

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.deleted==False).one().c
