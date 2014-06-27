from .model import *
from .account import Account

import ldap3

class InvalidUserException(Exception):
    pass

class LDAPLookup(object):
    """class that allows lookup of an individual in the UM directory
    based on Michigan ID number, uniqname, MCARD"""

    SERVER = "ldap.umich.edu"
    USERNAME = "cn=CSEG-McDirApp001,ou=Applications,o=services"
    BASE_DN = "ou=People,dc=umich,dc=edu"
    PASSWORD = ""
    ATTRIBUTES = ["uid", "entityid", "displayName"]
        
    def __init__(self):
        s = ldap3.Server(SERVER, port=636, use_ssl=True, get_info=ldap3.GET_ALL_INFO)
        self.__conn = ldap3.Connection(s, auto_bind=True, 
                user=USERNAME, password=PASSWORD,
                client_strategy=ldap3.STRATEGY_SYNC,
                authentication=ldap3.AUTH_SIMPLE
        )
                
    def __lookup(self, k, v):        
        query = "(%s=%s)" % (k, v)
        self.__conn.search(self.BASE_DN, 
                query,
                ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
                attributes=self.ATTRIBUTES
        )
        if len(self.__conn) == 0:
            raise InvalidUserException()
        return {
            "umid":self.__conn.response[0]["attributes"]["entityid"],
            "uniqname":self.__conn.response[0]["attributes"]["uid"],
            "name":self.__conn.response[0]["attributes"]["displayName"]
        }

    def lookup_umid(self, umid):
        return self.__lookup("entityid", umid)

    def lookup_uniqname(self, uniqname):
        return self.__lookup("uid", umid)


class User(Account):
    __tablename__ = 'users'
    __mapper_args__ = {'polymorphic_identity': 'user'}

    id = Column(Integer, primary_key=True, nullable=False)
    uniqname = Column(String(8), nullable=False, unique=True)
    umid = Column(String(8), nullable=False, unique=True)
    
    disabled = Column(Boolean, nullable=False, default=False)
    role = Column(Enum("user", "manager", "administrator", name="user_type"),
            nullable=False, default="user")

    __ldap = LDAPLookup()

    def __init__(self, uniqname, umid, name):
        self.uniqname = uniqname
        self.umid = umid
        self.name = name

    @classmethod
    def from_uniqname(cls, uniqname):
        u = DBSession.query(cls).filter(cls.uniqname == uniqname).first()
        if not u:
            u = cls(**cls.lookup_uniqname(uniqname))
            DBSession.add(u)
        return u
            
    @classmethod
    def from_umid(cls, umid):
        u = DBSession.query(cls).filter(cls.umid == umid).first()
        if not u:
            u = cls(**cls.lookup_umid(umid))
            DBSession.add(u)
        return u
