from .model import *
from . import account
from . import item

class NotesMissingException(Exception):
    pass

class Event(Base):
    __tablename__ = 'events'

    id        = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False) # user that performed the event
    notes     = Column(Text)

    deleted           = Column(Boolean, default=False, nullable=False)
    deleted_timestamp = Column(DateTime, nullable=True)
    deleted_user_id   = Column(Integer, ForeignKey("users.id"), nullable=True) # user that deleted the event

    type = Column(Enum("purchase", "deposit", "adjustment", "restock",
                       "inventory", "emptycashbox", "emptybitcoin", "reconcile",
                       "donation", "withdrawal",
                       name="event_type"), nullable=False)
    __mapper_args__ = {'polymorphic_on': type}


    def __init__(self, user, notes, timestamp=None):
        self.user_id = user.id
        self.notes = notes
        self.timestamp = timestamp or datetime.datetime.utcnow()

    def delete(self, user):
        self.deleted = True
        self.deleted_timestamp = datetime.datetime.utcnow()
        self.deleted_user_id = user.id

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    @limitable_all
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.deleted == False)\
                        .order_by(desc(cls.id))

    @classmethod
    def some(cls, count):
        return DBSession.query(cls)\
                        .filter(cls.deleted == False)\
                        .order_by(desc(cls.id))\
                        .limit(count).all()

    @classmethod
    def get_deleted(cls):
        return DBSession.query(cls)\
                        .filter(cls.deleted == True)\
                        .order_by(cls.id).all()

class Purchase(Event):
    __mapper_args__ = {'polymorphic_identity': 'purchase'}
    def __init__(self, user):
        Event.__init__(self, user, None)


class Deposit(Event):
    __mapper_args__ = {'polymorphic_identity': 'deposit'}
    def __init__(self, user):
        Event.__init__(self, user, None)


class Adjustment(Event):
    __mapper_args__ = {'polymorphic_identity': 'adjustment'}
    def __init__(self, admin, notes):
        if len(notes) < 3:
            raise NotesMissingException()
        Event.__init__(self, admin, notes)


class Restock(Event):
    __mapper_args__ = {'polymorphic_identity': 'restock'}
    def __init__(self, admin, timestamp=None):
        Event.__init__(self, admin, None, timestamp)


class Inventory(Event):
    __mapper_args__ = {'polymorphic_identity': 'inventory'}
    def __init__(self, admin):
        Event.__init__(self, admin, None)


class EmptyCashBox(Event):
    __mapper_args__ = {'polymorphic_identity': 'emptycashbox'}
    def __init__(self, admin):
        Event.__init__(self, admin, None)


class EmptyBitcoin(Event):
    __mapper_args__ = {'polymorphic_identity': 'emptybitcoin'}
    def __init__(self, admin):
        Event.__init__(self, admin, None)


class Reconcile(Event):
    __mapper_args__ = {'polymorphic_identity': 'reconcile'}
    def __init__(self, admin, notes):
        if len(notes) < 3:
            raise NotesMissingException()
        Event.__init__(self, admin, notes)


class Donation(Event):
    __mapper_args__ = {'polymorphic_identity': 'donation'}
    def __init__(self, admin, notes):
        if len(notes) < 3:
            raise NotesMissingException()
        Event.__init__(self, admin, notes)


class Withdrawal(Event):
    __mapper_args__ = {'polymorphic_identity': 'withdrawal'}
    def __init__(self, admin, notes):
        if len(notes) < 3:
            raise NotesMissingException()
        Event.__init__(self, admin, notes)


