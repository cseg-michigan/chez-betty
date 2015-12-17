from .model import *
from . import account
from . import event
from . import item
from . import box
from . import user
from chezbetty import utility

import arrow
from pyramid.threadlocal import get_current_registry


class Transaction(Base):
    __tablename__ = 'transactions'

    id                 = Column(Integer, primary_key=True, nullable=False)

    event_id           = Column(Integer, ForeignKey("events.id"))

    to_account_virt_id = Column(Integer, ForeignKey("accounts.id"))
    fr_account_virt_id = Column(Integer, ForeignKey("accounts.id"))
    to_account_cash_id = Column(Integer, ForeignKey("accounts.id"))
    fr_account_cash_id = Column(Integer, ForeignKey("accounts.id"))
    amount             = Column(Numeric, nullable=False)

                                        # Virtual Transaction Meaning     # Cash Transaction Meaning  # Notes required?
    type = Column(Enum("purchase",      # user_account -> chezbetty.        None
                       "deposit",
                       "cashdeposit",   # null         -> user_account.     null      -> cashbox.
                       "ccdeposit",     # null         -> user_account.     null      -> chezbetty
                       "btcdeposit",    # null         -> user_account      null      -> btcbox
                       "adjustment",    # chezbetty   <-> user              None                            Yes
                       "restock",       # chezbetty    -> null              chezbetty -> null
                       "inventory",     # chezbetty   <-> null              None
                       "emptycashbox",  # None                              cashbox   -> chezbetty
                       "emptybitcoin",  # None                              btcbox    -> chezbetty
                       "lost",          # None                              chezbetty/cashbox/btcbox -> null       Yes
                       "found",         # None                              null      -> chezbetty/cashbox/btcbox  Yes
                       "donation",      # null         -> chezbetty         null      -> chezbetty          Yes
                       "withdrawal",    # chezbetty    -> null              chezbetty -> null               Yes
                       name="transaction_type"), nullable=False)
    __mapper_args__ = {'polymorphic_on': type}


    to_account_virt = relationship(account.Account,
        foreign_keys=[to_account_virt_id,],
        backref="transactions_to_virt"
    )
    fr_account_virt = relationship(account.Account,
        foreign_keys=[fr_account_virt_id,],
        backref="transactions_from_virt"
    )

    to_account_cash = relationship(account.Account,
        foreign_keys=[to_account_cash_id,],
        backref="transactions_to_cash"
    )
    fr_account_cash = relationship(account.Account,
        foreign_keys=[fr_account_cash_id,],
        backref="transactions_from_cash"
    )
    event = relationship(event.Event,
        foreign_keys=[event_id,],
        backref="transactions"
    )


    def __init__(self, event, fr_acct_virt, to_acct_virt, fr_acct_cash, to_acct_cash, amount):
        self.to_account_virt_id = to_acct_virt.id if to_acct_virt else None
        self.fr_account_virt_id = fr_acct_virt.id if fr_acct_virt else None
        self.to_account_cash_id = to_acct_cash.id if to_acct_cash else None
        self.fr_account_cash_id = fr_acct_cash.id if fr_acct_cash else None

        self.to_acct_virt = to_acct_virt
        self.fr_acct_virt = fr_acct_virt
        self.to_acct_cash = to_acct_cash
        self.fr_acct_cash = fr_acct_cash

        self.event_id = event.id
        self.amount = amount

        # Update the balances of the accounts we are moving money between
        if to_acct_virt:
            to_acct_virt.balance += self.amount
        if fr_acct_virt:
            fr_acct_virt.balance -= self.amount

        if to_acct_cash:
            to_acct_cash.balance += self.amount
        if fr_acct_cash:
            fr_acct_cash.balance -= self.amount

    def update_amount(self, amount):
        # Remove the balance we added before (upon init or last update_amount)
        if self.to_acct_virt:
            self.to_acct_virt.balance -= self.amount
        if self.fr_acct_virt:
            self.fr_acct_virt.balance += self.amount
        if self.to_acct_cash:
            self.to_acct_cash.balance -= self.amount
        if self.fr_acct_cash:
            self.fr_acct_cash.balance += self.amount

        # Save the amount so we can subtract it later if needed
        self.amount = amount

        # Apply the new amount
        if self.to_acct_virt:
            self.to_acct_virt.balance += self.amount
        if self.fr_acct_virt:
            self.fr_acct_virt.balance -= self.amount
        if self.to_acct_cash:
            self.to_acct_cash.balance += self.amount
        if self.fr_acct_cash:
            self.fr_acct_cash.balance -= self.amount

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls)\
                        .filter(cls.id == id).one()

    @classmethod
    def get_balance(cls, trans_type, account_obj):
        return DBSession.query(coalesce(func.sum(cls.amount), 0).label("balance"))\
                     .join(event.Event)\
                     .filter(or_(cls.fr_account_cash_id==account_obj.id,
                                 cls.to_account_cash_id==account_obj.id,
                                 cls.fr_account_virt_id==account_obj.id,
                                 cls.to_account_virt_id==account_obj.id))\
                     .filter(cls.type==trans_type)\
                     .filter(event.Event.deleted==False).one()

    @classmethod
    def count(cls, trans_type=None):
        if not trans_type:
            return DBSession.query(func.count(cls.id).label('c'))\
                            .join(event.Event)\
                            .filter(event.Event.deleted==False).one().c
        else:
            return DBSession.query(func.count(cls.id).label('c'))\
                            .join(event.Event)\
                            .filter(cls.type==trans_type)\
                            .filter(event.Event.deleted==False).one().c

    @classmethod
    def total(cls, start=None, end=None):
        r = DBSession.query(func.sum(cls.amount).label('a'))\
                        .join(event.Event)\
                        .filter(event.Event.deleted==False)

        if start:
            r = r.filter(event.Event.timestamp>=start)
        if end:
            r = r.filter(event.Event.timestamp<end)

        return r.one().a or Decimal(0.0)

    # Returns an array of tuples where the first item is a millisecond timestamp,
    # the next is the total amount of debt, and the next is the total amount
    # of stored money for users.
    @classmethod
    def get_balance_total_daily(cls):
        rows = DBSession.query(cls.amount,
                               cls.type,
                               cls.to_account_virt_id,
                               cls.fr_account_virt_id,
                               event.Event.timestamp)\
                        .join(event.Event)\
                        .filter(or_(
                                  cls.type=='purchase',
                                  cls.type=='cashdeposit',
                                  cls.type=='ccdeposit',
                                  cls.type=='btcdeposit',
                                  cls.type=='adjustment'
                                ))\
                        .order_by(event.Event.timestamp)\
                        .all()
        return utility.timeseries_balance_total_daily(rows)


def __get_transactions_query(self):
    return object_session(self).query(Transaction)\
            .join(event.Event)\
            .filter(or_(
                      or_(
                        Transaction.to_account_virt_id == self.id,
                        Transaction.fr_account_virt_id == self.id,
                        Transaction.to_account_cash_id == self.id,
                        Transaction.fr_account_cash_id == self.id),
                      and_(
                        or_(event.Event.type == "purchase",
                            event.Event.type == "deposit"),
                        event.Event.user_id == self.id)))\
            .filter(event.Event.deleted==False)\
            .order_by(desc(event.Event.timestamp))\

@limitable_all
def __get_transactions(self):
    return __get_transactions_query(self)

@property
def __transactions(self):
    return __get_transactions(self)

account.Account.get_transactions_query = __get_transactions_query
account.Account.get_transactions = __get_transactions
account.Account.transactions = __transactions

# This is in a stupid place due to circular input problems
@limitable_all
def __get_events(self):
    return object_session(self).query(event.Event)\
            .join(Transaction)\
            .filter(or_(
                      or_(
                        Transaction.to_account_virt_id == self.id,
                        Transaction.fr_account_virt_id == self.id,
                        Transaction.to_account_cash_id == self.id,
                        Transaction.fr_account_cash_id == self.id),
                      and_(
                        or_(event.Event.type == "purchase",
                            event.Event.type == "deposit"),
                        event.Event.user_id == self.id)))\
            .filter(event.Event.deleted==False)\
            .order_by(desc(event.Event.timestamp))

@property
def __events(self):
    return __get_events(self).all()

account.Account.get_events = __get_events
account.Account.events = __events

# This is in a stupid place due to circular input problems
@property
def __total_deposit_amount(self):
    return object_session(self).query(func.sum(Transaction.amount).label("total"))\
            .join(event.Event)\
            .filter(and_(
                        Transaction.to_account_virt_id == self.id,
                        or_(Transaction.type == 'cashdeposit',
                            Transaction.type == 'ccdeposit',
                            Transaction.type == 'btcdeposit')))\
            .filter(event.Event.deleted==False).one().total or Decimal(0.0)
account.Account.total_deposits = __total_deposit_amount

# This is in a stupid place due to circular input problems
@property
def __total_purchase_amount(self):
    return object_session(self).query(func.sum(Transaction.amount).label("total"))\
            .join(event.Event)\
            .filter(and_(
                        Transaction.fr_account_virt_id == self.id,
                        Transaction.type == 'purchase'))\
            .filter(event.Event.deleted==False).one().total or Decimal(0.0)
account.Account.total_purchases = __total_purchase_amount

# This is in a stupid place due to circular input problems
@classmethod
@limitable_all
def __get_cash_events(cls):
    return DBSession.query(event.Event)\
            .join(Transaction)\
            .filter(or_(
                      Transaction.to_account_cash_id == account.get_cash_account("chezbetty").id,
                      Transaction.fr_account_cash_id == account.get_cash_account("chezbetty").id))\
            .filter(event.Event.deleted==False)\
            .order_by(desc(event.Event.timestamp))

event.Event.get_cash_events = __get_cash_events

# This is in a stupid place due to circular input problems
@classmethod
@limitable_all
def __get_restock_events(cls):
    return DBSession.query(event.Event)\
            .join(Transaction)\
            .filter(Transaction.type == 'restock')\
            .filter(event.Event.deleted==False)\
            .order_by(desc(event.Event.timestamp))

event.Event.get_restock_events = __get_restock_events

# This is in a stupid place due to circular input problems
@classmethod
@limitable_all
def __get_emptycash_events(cls):
    return DBSession.query(event.Event)\
            .join(Transaction)\
            .filter(or_(
                      Transaction.type == 'emptycashbox',
                      Transaction.type == 'emptybitcoin'))\
            .filter(event.Event.deleted==False)\
            .order_by(desc(event.Event.timestamp))

event.Event.get_emptycash_events = __get_emptycash_events

# This is in a stupid place due to circular input problems
@classmethod
@limitable_all
def __get_deposit_events(cls):
    return DBSession.query(event.Event)\
            .join(Transaction)\
            .filter(or_(
                      Transaction.type == 'cashdeposit',
                      Transaction.type == 'ccdeposit',
                      Transaction.type == 'btcdeposit'))\
            .filter(event.Event.deleted==False)\
            .order_by(desc(event.Event.timestamp))

event.Event.get_deposit_events = __get_deposit_events

# This is in a stupid place due to circular input problems
@property
def __days_since_last_purchase(self):
    last_purchase = object_session(self).query(event.Event)\
            .join(Transaction)\
            .filter(Transaction.fr_account_virt_id == self.id)\
            .filter(event.Event.type == 'purchase')\
            .filter(event.Event.deleted==False)\
            .order_by(desc(event.Event.timestamp)).first()

    if last_purchase:
        diff = arrow.now() - last_purchase.timestamp
        return diff.days
    else:
        return None

user.User.days_since_last_purchase = __days_since_last_purchase



class Purchase(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'purchase'}
    discount = Column(Numeric)

    def __init__(self, event, user, discount=None):
        chezbetty_v = account.get_virt_account("chezbetty")
        Transaction.__init__(self, event, user, chezbetty_v, None, None, Decimal(0.0))
        self.discount = discount


class Deposit(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'deposit'}

    @classmethod
    def deposits_by_period(cls, period, start=None, end=None):
        r = DBSession.query(cls.amount.label('summable'), event.Event.timestamp)\
                     .join(event.Event)\
                     .order_by(event.Event.timestamp)\
                     .filter(event.Event.deleted==False)
        if start:
            r = r.filter(event.Event.timestamp>=start.replace(tzinfo=None))
        if end:
            r = r.filter(event.Event.timestamp<end.replace(tzinfo=None))

        return utility.group(r.all(), period)


class CashDeposit(Deposit):
    __mapper_args__ = {'polymorphic_identity': 'cashdeposit'}

    CONTENTS_THRESHOLD = 1000
    REPEAT_THRESHOLD = 100

    def __init__(self, event, user, amount):
        cashbox_c = account.get_cash_account("cashbox")
        prev = cashbox_c.balance
        Transaction.__init__(self, event, None, user, None, cashbox_c, amount)
        new = cashbox_c.balance

        # It feels like the model should not have all of this application
        # specific logic in it. What does sending an email have to do with
        # representing a transaction. I think this should be moved to
        # datalayer.py which does handle application logic.
        try:
            if prev < CashDeposit.CONTENTS_THRESHOLD and new > CashDeposit.CONTENTS_THRESHOLD:
                self.send_alert_email(new)
            elif prev > CashDeposit.CONTENTS_THRESHOLD:
                pr = int((prev - CashDeposit.CONTENTS_THRESHOLD) / CashDeposit.REPEAT_THRESHOLD)
                nr = int((new - CashDeposit.CONTENTS_THRESHOLD) / CashDeposit.REPEAT_THRESHOLD)
                if pr != nr:
                    self.send_alert_email(new, nr)
        except:
            # Some error sending email. Let's not prevent the deposit from
            # going through.
            pass

    def send_alert_email(self, amount, repeat=0):
        settings = get_current_registry().settings

        SUBJECT = 'Time to empty Betty. Cash box has ${}.'.format(amount)
        TO = 'chez-betty@umich.edu'

        body = """
        <p>Betty's cash box is getting full. Time to go to the bank.</p>
        <p>The cash box currently contains ${}.</p>
        """.format(amount)
        if repeat > 8:
            body = """
            <p><strong>Yo! Get your shit together! That's a lot of cash lying
            around!</strong></p>""" + body
        elif repeat > 4:
            body = body + """
            <p><strong>But seriously, you should probably go empty the cashbox
            like, right meow.</strong></p>"""

        if 'debugging' in settings and bool(int(settings['debugging'])):
            SUBJECT = '[ DEBUG_MODE ] ' + SUBJECT
            body = """
            <p><em>This message was sent from a debugging session and may be
            safely ignored.</em></p>""" + body

        utility.send_email(TO=TO, SUBJECT=SUBJECT, body=body)


class CCDeposit(Deposit):
    __mapper_args__ = {'polymorphic_identity': 'ccdeposit'}

    stripe_id = Column(Text)
    cc_last4 = Column(Text)

    def __init__(self, event, user, amount, stripe_id, last4):
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, None, user, None, chezbetty_c, amount)
        self.stripe_id = stripe_id
        self.cc_last4 = last4


class BTCDeposit(Deposit):
    __mapper_args__ = {'polymorphic_identity': 'btcdeposit'}

    btctransaction = Column(String(64))
    address        = Column(String(64))
    amount_btc     = Column(Numeric, nullable=True)

    def __init__(self, event, user, amount, btctransaction, address, amount_btc):
        btcbox_c = account.get_cash_account("btcbox")
        Transaction.__init__(self, event, None, user, None, btcbox_c, amount)
        self.btctransaction = btctransaction
        self.address = address
        self.amount_btc = amount_btc

    def __getattr__(self, name):
        if name == 'img':
            return utility.string_to_qrcode(self.btctransaction)
        else:
            raise AttributeError

    @classmethod
    def from_address(cls, address):
        return DBSession.query(cls).join(event.Event)\
                        .filter(cls.address == address)\
                        .filter(event.Event.deleted == False).one()


class Adjustment(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'adjustment'}

    def __init__(self, event, user, amount):
        chezbetty_v = account.get_virt_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, user, None, None, amount)


class Restock(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'restock'}

    # Additional cost that should get distributed over the entire restock
    amount_restock_cost = Column(Numeric, nullable=True)

    def __init__(self, event, global_cost):
        chezbetty_v = account.get_virt_account("chezbetty")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, None, chezbetty_c, None, Decimal(0.0))
        self.amount_restock_cost = global_cost


class Inventory(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'inventory'}
    def __init__(self, event):
        chezbetty_v = account.get_virt_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, None, None, None, Decimal(0.0))


class EmptyCashBox(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'emptycashbox'}
    def __init__(self, event, amount):
        cashbox_c = account.get_cash_account("cashbox")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, None, None, cashbox_c, chezbetty_c, amount)


class EmptyBitcoin(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'emptybitcoin'}
    def __init__(self, event, amount):
        btnbox_c = account.get_cash_account("btcbox")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, None, None, btnbox_c, chezbetty_c, amount)


class Lost(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'lost'}
    def __init__(self, event, source_acct, amount):
        Transaction.__init__(self, event, None, None, source_acct, None, amount)


class Found(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'found'}
    def __init__(self, event, dest_acct, amount):
        Transaction.__init__(self, event, None, None, None, dest_acct, amount)


class Donation(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'donation'}
    def __init__(self, event, amount):
        chezbetty_v = account.get_virt_account("chezbetty")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, None, chezbetty_v, None, chezbetty_c, amount)


class Withdrawal(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'withdrawal'}
    def __init__(self, event, amount):
        chezbetty_v = account.get_virt_account("chezbetty")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, None, chezbetty_c, None, amount)


################################################################################
## SUB TRANSACTIONS
################################################################################

class SubTransaction(Base):
    __tablename__   = "subtransactions"

    id              = Column(Integer, primary_key=True, nullable=False)
    transaction_id  = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    amount          = Column(Numeric, nullable=False)
    type            = Column(Enum("purchaselineitem", "restocklineitem",
                                  "restocklinebox", "inventorylineitem",
                                  name="subtransaction_type"), nullable=False)
    item_id         = Column(Integer, ForeignKey("items.id"), nullable=True)
    quantity        = Column(Integer, nullable=False)
    wholesale       = Column(Numeric, nullable=False)

    # For restocks
    coupon_amount   = Column(Numeric, nullable=True) # Amount of discount on the item
    sales_tax       = Column(Boolean, nullable=True) # Whether sales tax was charged
    bottle_deposit  = Column(Boolean, nullable=True) # Whether there was a bottle deposit

    transaction     = relationship(Transaction, backref="subtransactions", cascade="all")
    item            = relationship(item.Item, backref="subtransactions")

    __mapper_args__ = {'polymorphic_on': type}

    def __init__(self, transaction, amount, item_id, quantity, wholesale):
        self.transaction_id = transaction.id
        self.amount = amount
        self.item_id = item_id
        self.quantity = quantity
        self.wholesale = wholesale

    def __getattr__(self, name):
        if name == 'deleted':
            return self.transaction.event.deleted
        else:
            raise AttributeError

    @classmethod
    @limitable_all
    def all_item(cls, id):
        return DBSession.query(cls)\
                        .join(Transaction)\
                        .join(event.Event)\
                        .filter(cls.item_id == id)\
                        .filter(event.Event.deleted==False)\
                        .order_by(desc(event.Event.timestamp))

    @classmethod
    @limitable_all
    def all_item_purchases(cls, id):
        return DBSession.query(cls)\
                        .join(Transaction)\
                        .join(event.Event)\
                        .filter(cls.item_id == id)\
                        .filter(event.Event.deleted==False)\
                        .filter(event.Event.type=="purchase")\
                        .order_by(desc(event.Event.timestamp))

    @classmethod
    @limitable_all
    def all_item_events(cls, id):
        return DBSession.query(cls)\
                        .join(Transaction)\
                        .join(event.Event)\
                        .filter(cls.item_id == id)\
                        .filter(event.Event.deleted==False)\
                        .filter(or_(event.Event.type=="inventory", event.Event.type =="restock"))\
                        .order_by(desc(event.Event.timestamp))

    @classmethod
    @limitable_all
    def all(cls, trans_type=None):
        if not trans_type:
            return DBSession.query(cls)\
                            .join(Transaction)\
                            .join(event.Event)\
                            .filter(event.Event.deleted==False)\
                            .order_by(desc(event.Event.timestamp))
        else:
            return DBSession.query(cls)\
                            .join(Transaction)\
                            .join(event.Event)\
                            .filter(cls.type==trans_type)\
                            .filter(event.Event.deleted==False)\
                            .order_by(desc(event.Event.timestamp))

class PurchaseLineItem(SubTransaction):
    __mapper_args__ = {'polymorphic_identity': 'purchaselineitem'}
    price           = Column(Numeric)
    def __init__(self, transaction, amount, item, quantity, price, wholesale):
        SubTransaction.__init__(self, transaction, amount, item.id, quantity, wholesale)
        self.price = price

    @classmethod
    def quantity_by_period(cls, period, start=None, end=None):
        r = DBSession.query(cls.quantity.label('summable'), event.Event.timestamp)\
                     .join(Transaction)\
                     .join(event.Event)\
                     .filter(event.Event.deleted==False)\
                     .order_by(event.Event.timestamp)
        if start:
            r = r.filter(event.Event.timestamp>=start.replace(tzinfo=None))
        if end:
            r = r.filter(event.Event.timestamp<end.replace(tzinfo=None))
        return utility.group(r.all(), period)

    @classmethod
    def virtual_revenue_by_period(cls, period, start=None, end=None):
        r = DBSession.query(cls.amount.label('summable'), event.Event.timestamp)\
                     .join(Transaction)\
                     .join(event.Event)\
                     .filter(event.Event.deleted==False)\
                     .order_by(event.Event.timestamp)
        if start:
            r = r.filter(event.Event.timestamp>=start.replace(tzinfo=None))
        if end:
            r = r.filter(event.Event.timestamp<end.replace(tzinfo=None))
        return utility.group(r.all(), period)

    @classmethod
    def profit_on_sales(cls, start=None, end=None):
        r = DBSession.query(func.sum(cls.amount-(cls.wholesale*cls.quantity)).label('p'))\
                        .join(Transaction)\
                        .join(event.Event)\
                        .filter(event.Event.deleted==False)
        if start:
            r = r.filter(event.Event.timestamp>=start.replace(tzinfo=None))
        if end:
            r = r.filter(event.Event.timestamp<end.replace(tzinfo=None))

        return r.one().p or Decimal(0.0)

    @classmethod
    def item_sale_quantities(cls, item_id):
        return DBSession.query(cls, event.Event)\
                        .join(Transaction)\
                        .join(event.Event)\
                        .filter(event.Event.deleted==False)\
                        .filter(cls.item_id==int(item_id))\
                        .order_by(event.Event.timestamp).all()


# This is slowww:
# @property
# def __number_sold(self):
#     return object_session(self).query(func.sum(PurchaseLineItem.quantity).label('c'))\
#                                .join(Transaction)\
#                                .join(event.Event)\
#                                .filter(PurchaseLineItem.item_id==self.id)\
#                                .filter(event.Event.deleted==False).one().c
# item.Item.number_sold = __number_sold


class RestockLineItem(SubTransaction):
    __mapper_args__ = {'polymorphic_identity': 'restocklineitem'}
    def __init__(self,
                 transaction,
                 amount,
                 item,
                 quantity,
                 wholesale,
                 coupon,
                 sales_tax,
                 bottle_deposit):
        SubTransaction.__init__(self, transaction, amount, item.id, quantity, wholesale)
        self.coupon_amount = coupon
        self.sales_tax = sales_tax
        self.bottle_deposit = bottle_deposit


class RestockLineBox(SubTransaction):
    __mapper_args__ = {'polymorphic_identity': 'restocklinebox'}
    box_id          = Column(Integer, ForeignKey("boxes.id"), nullable=True)

    box             = relationship(box.Box, backref="subtransactions")

    def __init__(self,
                 transaction,
                 amount,
                 box,
                 quantity,
                 wholesale,
                 coupon,
                 sales_tax,
                 bottle_deposit):
        self.transaction_id = transaction.id
        self.amount = amount
        self.box_id = box.id
        self.quantity = quantity
        self.wholesale = wholesale
        self.coupon_amount = coupon
        self.sales_tax = sales_tax
        self.bottle_deposit = bottle_deposit


class InventoryLineItem(SubTransaction):
    __mapper_args__    = {'polymorphic_identity': 'inventorylineitem'}
    quantity_predicted = synonym(SubTransaction.quantity)
    quantity_counted   = Column(Integer)

    def __init__(self, transaction, amount, item, quantity_predicted, quantity_counted, wholesale):
        SubTransaction.__init__(self, transaction, amount, item.id, quantity_predicted, wholesale)
        self.quantity_counted = quantity_counted



################################################################################
## SUBSUB TRANSACTIONS
################################################################################

# This is for tracking which items were in which boxes when we restocked

class SubSubTransaction(Base):
    __tablename__      = "subsubtransactions"

    id                 = Column(Integer, primary_key=True, nullable=False)
    subtransaction_id  = Column(Integer, ForeignKey("subtransactions.id"), nullable=False)
    type               = Column(Enum("restocklineboxitem",
                                     name="subsubtransaction_type"), nullable=False)
    item_id            = Column(Integer, ForeignKey("items.id"), nullable=True)
    quantity           = Column(Integer, nullable=False)

    subtransaction     = relationship(SubTransaction, backref="subsubtransactions", cascade="all")
    item               = relationship(item.Item, backref="subsubtransactions")

    __mapper_args__    = {'polymorphic_on': type}

    def __init__(self, subtransaction, item_id, quantity):
        self.subtransaction_id = subtransaction.id
        self.item_id = item_id
        self.quantity = quantity

    def __getattr__(self, name):
        if name == 'deleted':
            return self.subtransaction.transaction.event.deleted
        else:
            raise AttributeError

    @classmethod
    @limitable_all
    def all_item(cls, item_id):
        return DBSession.query(cls)\
                        .join(SubTransaction)\
                        .join(Transaction)\
                        .join(event.Event)\
                        .filter(cls.item_id == item_id)\
                        .filter(event.Event.deleted==False)\
                        .order_by(cls.id)


class RestockLineBoxItem(SubSubTransaction):
    __mapper_args__ = {'polymorphic_identity': 'restocklineboxitem'}
    def __init__(self, subtransaction, item, quantity):
        SubSubTransaction.__init__(self, subtransaction, item.id, quantity)



