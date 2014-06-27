from .model import *
from .transaction import Account

class LDAPUserNotFoundException(Exception):
    pass

class LDAPLookup(object):
    """class that allows lookup of an individual in the UM directory
    based on Michigan ID number, uniqname, MCARD"""

    USERNAME = "cn=CSEG-McDirApp001,ou=Applications,o=services"
    PASSWORD = ""

    def __init__(self):
        pass

    def lookup_umid(self, umid):
        pass

    def lookup_uniqname(self, uniqname):
        pass


class User(Account):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, nullable=False)
    uniqname = Column(String(8), nullable=False, unique=True)
    umid = Column(String(8), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    disabled = Column(Boolean, nullable=False, default=False)
    role = Column(Enum("user", "manager", "administrator", name="user_type"),
            nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.datetime.now)

    @classmethod
    def from_uniqname(cls, uniqname):
        pass

    @classmethod
    def from_umid(cls, uniqname):
        pass

    @classmethod
    def from_idcard(cls, idcard):
        pass

    def __init__(self, uniqname, umid, display_name):
        self.uniqname = uniqname
        self.umid = umid
        self.display_name = display_name


