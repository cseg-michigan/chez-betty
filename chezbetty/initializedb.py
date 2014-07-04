import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

import models.account as account
from models.item import Item
from models.user import User
from models.model import *
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

    with transaction.manager:
        DBSession.add(Item(
           "Nutrigrain Raspberry",
           "038000358210",
           14.37,
           0.47,
           1,
           True
        ))
        DBSession.add(Item(
           "Clif Bar: Chocolate Chip",
           "722252100900",
           1.25,
           1.17,
           5,
           True
        ))
        DBSession.add(Item(
           "Clif Bar: Crunchy Peanut Butter",
           "722252101204",
           1.25,
           1.14,
           5,
           True
        ))
        DBSession.add(Item(
            "Coke (12 oz)",
            "04963406",
            0.42,
            0.37,
            12,
            True
        ))
        user = User(
           "zakir",
           "95951361",
           "Zakir Durumeric"
        )
        user.role = "administrator"
        user.password = "test"
        DBSession.add(user)
        user = User(
           "bradjc",
           "11519022",
           "Brad Campbell"
        )
        user.role = "administrator"
        user.password = "test"
        DBSession.add(user)
        user = User(
               "ppannuto",
               "64880621",
               "Pat Pannuto"
               )
        user.role = "administrator"
        user.password = "test2"
        DBSession.add(user)
        account.get_virt_account("chezbetty")
        account.get_cash_account("cashbox")
        account.get_cash_account("chezbetty")
        account.get_cash_account("btcbox")

if __name__ == "__main__":
    main()
