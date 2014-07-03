from .model import *
from . import account
from . import item

class NotesMissingException(Exception):
    pass

class Event(Base):
    __tablename__ = 'events'

    id        = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=True) # user that performed the transaction
    notes     = Column(Text)

    type = Column(Enum("purchase", "deposit", "adjustment", "restock",
                       "inventory", "emptycashbox", "emptybitcoin", "reconcile",
                       "donation", "withdrawal",
                       name="event_type"), nullable=False)
    __mapper_args__ = {'polymorphic_on': type}


    def __init__(self, user, notes):
        self.user_id = user.id
        self.notes = notes

    @classmethod
    def from_id(cls, id):
        e = DBSession.query(cls).filter(cls.id == id).one()
        return e


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
    def __init__(self, admin):
        Event.__init__(self, admin, None)


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


