from pyramid.security import authenticated_userid
import hashlib
import binascii
import os
from .model import *
from .account import Account
from .transaction import Transaction
from .event import Event

import ldap3

class InvalidUserException(Exception):
    pass


class LDAPLookup(object):
    """class that allows lookup of an individual in the UM directory
    based on Michigan ID number, uniqname, MCARD"""

    SERVER = None
    USERNAME = None
    BASE_DN = "ou=People,dc=umich,dc=edu"
    PASSWORD = None
    ATTRIBUTES = ["uid", "entityid", "displayName"]

    def __init__(self):
        self.__conn = None

    def __connect(self):
        if not self.__conn:
            s = ldap3.Server(self.SERVER, port=636, use_ssl=True, get_info=ldap3.GET_ALL_INFO)
            self.__conn = ldap3.Connection(s, auto_bind=True,
                    user=self.USERNAME, password=self.PASSWORD,
                    client_strategy=ldap3.STRATEGY_SYNC,
                    authentication=ldap3.AUTH_SIMPLE
            )


    def __lookup(self, k, v):
        self.__connect()
        query = "(%s=%s)" % (k, v)
        try:
            self.__conn.search(self.BASE_DN,
                    query,
                    ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
                    attributes=self.ATTRIBUTES
            )
        except:
            # sometimes our connections time out
            self.__conn = None
            self.__connect()
            self.__conn.search(self.BASE_DN,
                    query,
                    ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
                    attributes=self.ATTRIBUTES
            )

        if len(self.__conn.response) == 0:
            raise InvalidUserException()
        return {
            "umid":self.__conn.response[0]["attributes"]["entityid"][0],
            "uniqname":self.__conn.response[0]["attributes"]["uid"][0],
            "name":self.__conn.response[0]["attributes"]["displayName"][0]
        }

    def lookup_umid(self, umid):
        return self.__lookup("entityid", umid)

    def lookup_uniqname(self, uniqname):
        return self.__lookup("uid", umid)


class User(Account):
    __tablename__ = 'users'
    __mapper_args__ = {'polymorphic_identity': 'user'}

    id        = Column(Integer, ForeignKey("accounts.id"), primary_key=True)
    uniqname  = Column(String(8), nullable=False, unique=True)
    umid      = Column(String(8), unique=True)
    _password = Column("password", String(255))
    _salt     = Column("salt", String(255))
    enabled   = Column(Boolean, nullable=False, default=True)
    role      = Column(Enum("user", "serviceaccount", "manager", "administrator", name="user_type"),
                       nullable=False, default="user")

    administrative_events = relationship(Event, backref="admin")
    __ldap = LDAPLookup()

    def __init__(self, uniqname, umid, name):
        self.enabled = True
        self.uniqname = uniqname
        self.umid = umid
        self.name = name
        self.balance = 0.0

    def __str__(self):
        return "<User: id {}, uniqname {}, umid {}, name {}, balance {}>".\
                format(self.id, self.uniqname, self.umid, self.name, self.balance)

    @classmethod
    def from_id(cls, id):
        u = DBSession.query(cls).filter(cls.id == id).one()
        return u

    @classmethod
    def from_uniqname(cls, uniqname):
        u = DBSession.query(cls).filter(cls.uniqname == uniqname).first()
        if not u:
            u = cls(**cls.__ldap.lookup_uniqname(uniqname))
            DBSession.add(u)
        return u

    @classmethod
    def from_umid(cls, umid):
        u = DBSession.query(cls).filter(cls.umid == umid).first()
        if not u:
            u = cls(**cls.__ldap.lookup_umid(umid))
            DBSession.add(u)
        return u

    def __make_salt(self):
        return binascii.b2a_base64(open("/dev/urandom", "rb").read(32))[:-3].decode("ascii")

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._salt = self.__make_salt()
        salted = (self._salt + password).encode('utf-8')
        self._password = hashlib.sha256(salted).hexdigest()

    def check_password(self, cand):
        if not self._salt:
            return False
        salted = (self._salt + cand).encode('utf-8')
        c = hashlib.sha256(salted).hexdigest()
        return c == self._password


def get_user(request):
    login = authenticated_userid(request)
    if not login:
        return None
    return DBSession.query(User).filter(User.uniqname == login).one()


def groupfinder(userid, request):
    user = User.from_uniqname(userid)
    if user.role == "user":
        return ["user",]
    elif user.role == "manager":
        return ["user","manager"]
    elif user.role == "administrator":
        return ["user","manager","admin", "serviceaccount"]
    elif user.role == "serviceaccount":
        return ["user", "serviceaccount"]
