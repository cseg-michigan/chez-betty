import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

try:
    import models.account as account
    from models.item import Item
    from models.user import User
    from models.vendor import Vendor
    from models.box import Box
    from models.request import Request
    from models.item_vendor import ItemVendor
    from models.box_vendor import BoxVendor
    from models.box_item import BoxItem
    from models.announcement import Announcement
    from models.model import *
    from models.transaction import *
    from models.btcdeposit import BtcPendingDeposit
    from models.receipt import Receipt
except ImportError:
    print("relative import struggles? this script has to be run in the")
    print("root code directory (i.e. where models.py et al are)")
    raise

def usage(argv):
    print("ERR: Script requires config file (probably development.ini) as an argument")
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
#    Base.metadata.create_all(engine)


    with transaction.manager:

        boxes = Box.all()
        for box in boxes:
            total_items = box.subitem_count
            for bi in box.items:
                bi.percentage = round((bi.quantity/total_items)*100, 2)

if __name__ == "__main__":
    main()
