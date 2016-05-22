import datetime
import functools
from decimal import Decimal
from decimal import ROUND_HALF_UP
import decimal
from sqlalchemy import (
    LargeBinary,
    Column,
    Index,
    Integer,
    String,
    Numeric,
    Text,
    Enum,
    ForeignKey,
    Boolean,
    LargeBinary,
    desc,
    asc
    )

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    validates,
    relationship,
    object_session,
    backref
    )

from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import synonym
from sqlalchemy.sql.expression import or_, and_, func, exists
from sqlalchemy.sql.functions import coalesce
from zope.sqlalchemy import ZopeTransactionExtension

from .history_meta import Versioned, versioned_session

from pyramid.security import Allow, Everyone

DBSession = versioned_session(scoped_session(sessionmaker(extension=ZopeTransactionExtension())))
Base = declarative_base()

class RootFactory(object):
    __name__ = None
    __parent__ = None
    __acl__ = [
        (Allow, 'user', 'user'),
        (Allow, 'serviceaccount', 'service'),
        (Allow, 'manager', 'manage'),
        (Allow, 'admin', 'admin'),
    ]

    def __init__(self, request):
        pass

# Decorator that adds optional limit parameter to any all() query
def limitable_all(fn_being_decorated):
    @functools.wraps(fn_being_decorated)
    def wrapped_fn(*args, limit=None, offset=None, count=False, **kwargs):
        q = fn_being_decorated(*args, **kwargs)
        if offset:
            q = q.offset(offset)
        if limit:
            if count:
                return q.limit(limit).all(), q.count()
            else:
                return q.limit(limit).all()
        else:
            if count:
                return q.all(), q.count()
            else:
                return q.all()
    return wrapped_fn

# Helper that checks for common get parameters for limitable queries
def limitable_request(request, fn, prefix=None, limit=None, count=False):
    if prefix:
        limit_str = prefix + '_limit'
        offset_str = prefix + '_offset'
    else:
        limit_str = 'limit'
        offset_str = 'offset'
    try:
        LIMIT  = int(request.GET[limit_str ]) if limit_str  in request.GET else limit
    except ValueError:
        LIMIT  = limit
    try:
        OFFSET = int(request.GET[offset_str]) if offset_str in request.GET else None
    except ValueError:
        OFFSET = None

    if count:
        r, r_tot = fn(limit=LIMIT, offset=OFFSET, count=count)
        if LIMIT is None or r_tot <= LIMIT:
            r_tot = 0
        return r, r_tot
    else:
        return fn(limit=LIMIT, offset=OFFSET, count=count)

