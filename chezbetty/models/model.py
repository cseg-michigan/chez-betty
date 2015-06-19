import datetime
import functools
from decimal import Decimal
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
    DateTime,
    ForeignKey,
    Boolean,
    LargeBinary,
    desc
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
from sqlalchemy.sql.expression import or_, and_, func
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
def limitable_request(request, fn, limit=None, count=False):
    try:
        LIMIT  = int(request.GET['limit' ]) if 'limit'  in request.GET else limit
    except ValueError:
        LIMIT  = limit
    try:
        OFFSET = int(request.GET['offset']) if 'offset' in request.GET else None
    except ValueError:
        OFFSET = None
    return fn(limit=LIMIT, offset=OFFSET, count=count)

