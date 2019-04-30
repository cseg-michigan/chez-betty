from .model import *
from . import event
from . import user

class Receipt(Base):
    __tablename__ = 'receipts'

    id       = Column(Integer, primary_key=True, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    receipt  = Column(LargeBinary, nullable=False)
    deleted  = Column(Boolean, default=False, nullable=False)

    event    = relationship(event.Event, foreign_keys=[event_id], backref="receipts")
    user     = relationship(user.User, foreign_keys=[user_id], backref="receipts")

    def __init__(self, event, user, receipt, deleted=False):
        self.event_id = event.id
        self.user_id  = user.id
        receipt.seek(0)
        self.receipt  = receipt.read()
        self.deleted  = deleted

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    ## Move receipts from one event to a new one. This is useful in particular
    ## if a restock is undone and then re-submitted but the receipts are still
    ## valid.
    @classmethod
    def transfer(cls, old_event_id, new_event_id):
        matching_receipts = DBSession.query(cls).filter(cls.event_id == old_event_id).all()
        for receipt in matching_receipts:
            receipt.event_id = new_event_id
