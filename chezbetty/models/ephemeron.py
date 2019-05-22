from .model import *

from sqlalchemy_utils import ArrowType

class Ephemeron(Base):
    __tablename__ = 'ephemera'

    id        = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(ArrowType, nullable=False, default=datetime.datetime.utcnow)
    name      = Column(String(255), nullable=False, unique=True)
    value     = Column(Text, nullable=False)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.deleted==False)\
                        .order_by(cls.name).all()

    @classmethod
    def from_name(cls, name):
        return DBSession.query(cls).filter(cls.name == name).one_or_none()

    @classmethod
    def add_list(cls, name, new_item):
        out = ''
        initial = DBSession.query(cls).filter(cls.name == name).one_or_none()
        if initial:
            initial.value = '{},{}'.format(initial.value, new_item)
            out = initial.value
        else:
            toadd = Ephemeron(name, new_item)
            DBSession.add(toadd)
            out = new_item
        DBSession.flush()
        return out

    @classmethod
    def add_decimal(cls, name, new_decimal):
        total_stored = Decimal(0)

        existing = Ephemeron.from_name(name)
        if existing:
            total_stored = Decimal(existing.value)
            total_stored += new_decimal
            existing.value = '{}'.format(total_stored)
        else:
            total_stored = new_decimal
            new_temp_deposit = Ephemeron(name, '{}'.format(new_decimal))
            DBSession.add(new_temp_deposit)

        DBSession.flush()
        return total_stored

    @classmethod
    def set_string(cls, name, save_string):
        existing = Ephemeron.from_name(name)
        if existing:
            existing.value = save_string
        else:
            new_string = Ephemeron(name, save_string)
            DBSession.add(new_string)

        DBSession.flush()
