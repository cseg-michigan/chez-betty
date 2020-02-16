from pyramid.security import authenticated_userid
import hashlib
import binascii
import os
from .model import *
from . import account
from . import event
from . import request
from . import request_post
from chezbetty import utility

import ldap3
import random
import string

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
    # http://www.itcs.umich.edu/itcsdocs/r1463/attributes-for-ldap.html
    DETAILS_ATTRIBUTES = [
            # Could be interesting but require extra perm's from ITS
            #"umichInstRoles",
            #"umichAlumStatus",
            #"umichAAAcadProgram",
            #"umichAATermStatus",
            #"umichHR",
            "notice",
            "ou",
            "umichDescription",
            "umichTitle",
            ]

    def __init__(self):
        self.__conn = None

    def __connect(self):
        if not self.__conn:
            s = ldap3.Server(self.SERVER, port=636, use_ssl=True, get_info=ldap3.ALL)
            self.__conn = ldap3.Connection(s, auto_bind=True,
                    user=self.USERNAME, password=self.PASSWORD,
                    client_strategy=ldap3.SYNC,
                    authentication=ldap3.SIMPLE
            )


    def __do_lookup(self, k, v, attributes, full_dict=False):
        self.__connect()
        query = "(%s=%s)" % (k, v)
        try:
            self.__conn.search(self.BASE_DN,
                    query,
                    ldap3.SUBTREE,
                    attributes=attributes
            )
        except:
            # sometimes our connections time out
            self.__conn = None
            self.__connect()
            self.__conn.search(self.BASE_DN,
                    query,
                    ldap3.SUBTREE,
                    attributes=attributes
            )

        if len(self.__conn.response) == 0:
            raise InvalidUserException()

        if full_dict:
            return self.__conn.response[0]["attributes"]

        return {
            "umid":self.__conn.response[0]["attributes"]["entityid"],
            "uniqname":self.__conn.response[0]["attributes"]["uid"][0],
            "name":self.__conn.response[0]["attributes"]["displayName"][0]
        }

    def __lookup(self, k, v):
        return self.__do_lookup(k, v, self.ATTRIBUTES)

    def __detail_lookup(self, k, v):
        return self.__do_lookup(k, v,
                self.ATTRIBUTES + self.DETAILS_ATTRIBUTES,
                full_dict=True,
                )

    def lookup_umid(self, umid, details=False):
        if details:
            return self.__detail_lookup("entityid", umid)
        else:
            return self.__lookup("entityid", umid)

    def lookup_uniqname(self, uniqname, details=False):
        if details:
            return self.__detail_lookup("uid", uniqname)
        else:
            return self.__lookup("uid", uniqname)


class User(account.Account):
    __tablename__ = 'users'
    __mapper_args__ = {'polymorphic_identity': 'user'}

    id        = Column(Integer, ForeignKey("accounts.id"), primary_key=True)
    uniqname  = Column(String(8), nullable=False, unique=True)
    umid      = Column(String(8), unique=True)
    _password = Column("password", String(255))
    _salt     = Column("salt", String(255))
    enabled   = Column(Boolean, nullable=False, default=True)
    archived  = Column(Boolean, nullable=False, default=False)
    role      = Column(Enum("user", "volunteer", "serviceaccount", "manager", "administrator", name="user_type"),
                       nullable=False, default="user")

    administrative_events = relationship(event.Event, foreign_keys=[event.Event.user_id], backref="admin")
    events_deleted        = relationship(event.Event, foreign_keys=[event.Event.deleted_user_id], backref="deleted_user")
    requests              = relationship(request.Request, foreign_keys=[request.Request.user_id], backref="user")
    request_posts         = relationship(
                              request_post.RequestPost,
                              foreign_keys=[request_post.RequestPost.user_id],
                              backref="user",
                            )

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
        return DBSession.query(cls).filter(cls.id == id).one()

    def get_details(self):
        return self.__ldap.lookup_uniqname(self.uniqname, details=True)

    @classmethod
    def from_uniqname(cls, uniqname, local_only=False):
        u = DBSession.query(cls).filter(cls.uniqname == uniqname).first()
        if not u and not local_only:
            u = cls(**cls.__ldap.lookup_uniqname(uniqname))
            DBSession.add(u)
        return u

    @classmethod
    def from_umid(cls, umid, create_if_never_seen=False):
        u = DBSession.query(cls).filter(cls.umid == umid).first()
        if not u:
            if create_if_never_seen:
                u = cls(**cls.__ldap.lookup_umid(umid))
                DBSession.add(u)
                utility.new_user_email(u)
            else:
                raise InvalidUserException()
        return u

    @classmethod
    def from_fuzzy(cls, search_str, any=True):
        q = DBSession.query(cls)\
                     .filter(or_(
                            cls.uniqname.ilike('%{}%'.format(search_str)),
                            cls.umid.ilike('%{}%'.format(search_str)),
                            cls.name.ilike('%{}%'.format(search_str))
                      ))
        if not any:
            q = q.filter(cls.enabled)\
                 .filter(cls.archived==False)

        return q.all()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .order_by(cls.name)\
                        .all()

    @classmethod
    def count(cls):
        return DBSession.query(func.count(cls.id).label('c'))\
                        .filter(cls.role != 'serviceaccount')\
                        .filter(cls.archived == False)\
                        .filter(cls.enabled == True)\
                        .one().c

    @classmethod
    def get_admins(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .filter(cls.role=='administrator').all()

    @classmethod
    def get_shame_users(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .filter(cls.balance < -5)\
                        .order_by(cls.balance).all()

    @classmethod
    def get_normal_users(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .filter(cls.archived == False)\
                        .order_by(cls.name).all()

    @classmethod
    def get_archived_users(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled)\
                        .filter(cls.archived == True)\
                        .order_by(cls.name).all()

    @classmethod
    def get_disabled_users(cls):
        return DBSession.query(cls)\
                        .filter(cls.enabled == False)\
                        .order_by(cls.name).all()

    @classmethod
    def get_users_below_balance(cls, balance):
        '''
        Get all users with a balance below `balance`.
        '''
        return DBSession.query(cls)\
                        .filter(cls.enabled == True)\
                        .filter(cls.balance < balance)\
                        .all()

    @classmethod
    def get_number_new_users(cls, start=None, end=None):
        r = DBSession.query(cls)\
                        .filter(cls.enabled == True)

        if start:
            r = r.filter(cls.created_at>=start)
        if end:
            r = r.filter(cls.created_at<end)

        return r.count()

    @classmethod
    def get_users_total(cls):
        return DBSession.query(func.sum(User.balance).label("total_balance"))\
                        .one().total_balance or Decimal(0.0)

    # Sum the total amount of money in user accounts that we are holding for
    # users. This is different from just getting the total because it doesn't
    # count users with negative balances
    @classmethod
    def get_amount_held(cls):
        return DBSession.query(func.sum(User.balance).label("total_balance"))\
                        .filter(User.balance>0)\
                        .one().total_balance or Decimal(0.0)

    @classmethod
    def get_amount_owed(cls):
        return DBSession.query(func.sum(User.balance).label("total_balance"))\
                        .filter(User.balance<0)\
                        .one().total_balance or Decimal(0.0)

    # Sum the amount of debt that has been moved to archived user
    @classmethod
    def get_debt_forgiven(cls):
        return DBSession.query(func.sum(User.archived_balance).label("total_balance"))\
                        .filter(User.archived_balance<0)\
                        .filter(User.archived==True)\
                        .one().total_balance or Decimal(0.0)

    # Sum the amount of user balances that we have tentatively absorbed into the
    # main betty balance
    @classmethod
    def get_amount_absorbed(cls):
        return DBSession.query(func.sum(User.archived_balance).label("total_balance"))\
                        .filter(User.archived_balance>0)\
                        .filter(User.archived==True)\
                        .one().total_balance or Decimal(0.0)

    @classmethod
    def get_user_count_cumulative(cls):
        rows = DBSession.query(cls.created_at)\
                        .order_by(cls.created_at)\
                        .all()
        return utility.timeseries_cumulative(rows)

    def purchase_threshold_check(self, limit=None):
        count = 0
        for e in self.events:
            if e.type == 'purchase':
                count += 1
        return count <= limit

    def deposit_threshold_check(self, limit=None):
        count = 0
        for e in self.events:
            if e.type == 'deposit':
                count += 1
        return count <= limit

    def iterate_recent_items(self, limit=None, allow_duplicates=False, pictures_only=True):
        cap_search = 20
        items = set()
        count = 0
        for e in self.events:
            if e.type == 'purchase':
                for transaction in e.transactions:
                    if transaction.type == 'purchase':
                        for line_item in transaction.subtransactions:
                            cap_search -= 1
                            if cap_search == 0:
                                return
                            if (line_item.item not in items) or allow_duplicates:
                                if (line_item.item.img) or not pictures_only:
                                    count += 1
                                    if limit is not None and count > limit:
                                        return
                                    yield line_item.item
                                    items.add(line_item.item)

    def __make_salt(self):
        return binascii.b2a_base64(open("/dev/urandom", "rb").read(32))[:-3].decode("ascii")

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        if password == '':
            # Use this to clear the password so the user can't login
            self._password = None
        else:
            self._salt = self.__make_salt()
            salted = (self._salt + password).encode('utf-8')
            self._password = hashlib.sha256(salted).hexdigest()

    def random_password(self):
        password = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(6))
        self._salt = self.__make_salt()
        salted = (self._salt + password).encode('utf-8')
        self._password = hashlib.sha256(salted).hexdigest()
        return password

    def check_password(self, cand):
        if not self._salt:
            return False
        salted = (self._salt + cand).encode('utf-8')
        c = hashlib.sha256(salted).hexdigest()
        return c == self._password

    @property
    def has_password(self):
        return self._password != None

    @property
    def role_human_readable(self):
        roles = {'user': 'User',
                 'volunteer': 'Volunteer',
                 'serviceaccount': 'Service Account',
                 'manager': 'Manager',
                 'administrator': 'Administrator'}
        return roles[self.role]


def get_user(request):
    login = authenticated_userid(request)
    if not login:
        return None
    return DBSession.query(User).filter(User.uniqname == login).one()


# This is in a stupid place due to circular input problems
@property
def __user_from_foreign_key(self):
    return User.from_id(self.user_id)
event.Event.user = __user_from_foreign_key


def groupfinder(userid, request):
    user = User.from_uniqname(userid)
    if user.role == "user":
        return ["user",]
    elif user.role == "volunteer":
        return ["user"]
    elif user.role == "manager":
        return ["user","manager"]
    elif user.role == "administrator":
        return ["user","manager","admin","serviceaccount"]
    elif user.role == "serviceaccount":
        return ["serviceaccount"]
