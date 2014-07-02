import os
import sys
import transaction

from sqlalchemy import engine_from_config
from sqlalchemy.sql import func

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from models.account import Account, make_account
from models.item import Item
from models.user import User
from models.model import *
from models.transaction import *
from models.cashtransaction import *
from models.account import Account
from models.user import User
from models.item import Item
from models.transaction import *

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
        
    print(DBSession.query(func.sum(SubTransaction.quantity)).join(Item).group_by(Item.id).order_by(desc(func.sum(SubTransaction.quantity))).all())

if __name__ == "__main__":
    main()
