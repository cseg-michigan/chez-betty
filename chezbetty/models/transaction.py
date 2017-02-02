from .model import *
from . import account
from . import event
from . import item
from . import box
from . import user
from chezbetty import utility

import arrow
from pyramid.threadlocal import get_current_registry
from sqlalchemy.sql import extract


def datefilter_one_or_zero(label=None):
    def wrap(fn_being_decorated):
        @functools.wraps(fn_being_decorated)
        def wrapped_fn(*args,
                start=None, end=None,
                dow_start=None, dow_end=None,
                weekend_only=False, weekday_only=False,
                business_hours_only=False, evening_hours_only=False, latenight_hours_only=False,
                ugos_closed_hours=False,
                **kwargs):
            r = fn_being_decorated(*args, **kwargs)

            if start:
                r = r.filter(event.Event.timestamp>=start.replace(tzinfo=None))
            if end:
                r = r.filter(event.Event.timestamp<end.replace(tzinfo=None))

            # n.b. this is a postgres function we're calling here
            # The day of the week (0 - 6; Sunday is 0) (for timestamp values only)
            # n0 m1 t2 w3 h4 f5 s6
            if dow_start:
                r = r.filter(extract('dow', event.Event.timestamp) >= dow_start)
            if dow_end:
                r = r.filter(extract('dow', event.Event.timestamp) < dow_start)
            if weekend_only:
                r = r.filter(or_(
                    extract('dow', event.Event.timestamp) == 0,
                    extract('dow', event.Event.timestamp) == 6
                ))
            if weekday_only:
                r = r.filter(extract('dow', event.Event.timestamp) > 0)
                r = r.filter(extract('dow', event.Event.timestamp) < 6)

            if business_hours_only:
                r = r.filter(extract('hour', event.Event.timestamp) >= 8)
                r = r.filter(extract('hour', event.Event.timestamp) < 17)
            if evening_hours_only:
                r = r.filter(extract('hour', event.Event.timestamp) >= 17)
            if latenight_hours_only:
                r = r.filter(extract('hour', event.Event.timestamp) < 8)
            if ugos_closed_hours:
                r = r.filter(or_(
                    # m-th 8-mid
                    and_(
                        extract('hour', event.Event.timestamp) < 8, # 8-mid
                        extract('dow', event.Event.timestamp) > 0,  # no sunday
                        extract('dow', event.Event.timestamp) < 5,  # no fri/sat
                        ),
                    # fr 8-8pm
                    and_(
                        or_(
                            extract('hour', event.Event.timestamp) < 8,   # before open
                            extract('hour', event.Event.timestamp) >= 20, # after close
                            ),
                        extract('dow', event.Event.timestamp) == 5,       # friday
                        ),
                    # sat noon-5pm
                    and_(
                        or_(
                            extract('hour', event.Event.timestamp) < 12,   # before open
                            extract('hour', event.Event.timestamp) >= 17, # after close
                            ),
                        extract('dow', event.Event.timestamp) == 6,       # saturday
                        ),
                    # sun 3pm-11pm
                    and_(
                        or_(
                            extract('hour', event.Event.timestamp) < 15,   # before open
                            extract('hour', event.Event.timestamp) >= 23, # after close
                            ),
                        extract('dow', event.Event.timestamp) == 0,       # sunday
                        ),
                    ))


            if label:
                return getattr(r.one(), label) or Decimal(0.0)
            else:
                return r.one() or Decimal(0.0)
        return wrapped_fn
    return wrap

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
                       "restock",       # chezbetty    -> null              chezbetty -> null/reimbursee
                       "inventory",     # chezbetty   <-> null              None
                       "emptycashbox",  # None                              cashbox   -> safe
                       "emptysafe",     # None                              safe      -> chezbetty
                       "emptybitcoin",  # None                              btcbox    -> chezbetty
                       "lost",          # None                              chezbetty/cashbox/btcbox -> null       Yes
                       "found",         # None                              null      -> chezbetty/cashbox/btcbox  Yes
                       "donation",      # null         -> chezbetty         null      -> chezbetty          Yes
                       "withdrawal",    # chezbetty    -> null              chezbetty -> null               Yes
                       "reimbursement", # None                              reimbursee-> null
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
    @datefilter_one_or_zero(label=None)
    def get_balance(cls, trans_type, account_obj):
        r = DBSession.query(coalesce(func.sum(cls.amount), 0).label("balance"))\
                     .join(event.Event)\
                     .filter(or_(cls.fr_account_cash_id==account_obj.id,
                                 cls.to_account_cash_id==account_obj.id,
                                 cls.fr_account_virt_id==account_obj.id,
                                 cls.to_account_virt_id==account_obj.id))\
                     .filter(cls.type==trans_type)\
                     .filter(event.Event.deleted==False)
        return r

    @classmethod
    def count(cls, *, trans_type=None, start=None, end=None):
        r = DBSession.query(func.count(cls.id).label('c'))\
                            .join(event.Event)\
                            .filter(event.Event.deleted==False)

        if trans_type:
            r = r.filter(cls.type==trans_type)
        if start:
            r = r.filter(event.Event.timestamp>=start)
        if end:
            r = r.filter(event.Event.timestamp<end)

        return r.one().c

    @classmethod
    def distinct(cls, *, distinct_on=None, start=None, end=None):
        r = DBSession.query(cls).join(event.Event)\
                .filter(event.Event.deleted==False)

        if start:
            r = r.filter(event.Event.timestamp>=start)
        if end:
            r = r.filter(event.Event.timestamp<end)

        if distinct_on is None:
            raise NotImplementedError("required argument distinct_on missing")

        r = r.distinct(distinct_on)

        return r.count()

    @classmethod
    @datefilter_one_or_zero(label='a')
    def total(cls):
        r = DBSession.query(func.sum(cls.amount).label('a'))\
                        .join(event.Event)\
                        .filter(event.Event.deleted==False)
        return r

    # Get the total amount of discounts people have received for keeping
    # money in their account
    @classmethod
    def discounts(cls, start=None, end=None):
        r = DBSession.query(func.sum((cls.amount / (1-cls.discount)) - cls.amount).label('d'))\
                        .join(event.Event)\
                        .filter(cls.discount > 0)\
                        .filter(event.Event.deleted==False)

        if start:
            r = r.filter(event.Event.timestamp>=start)
        if end:
            r = r.filter(event.Event.timestamp<end)

        return r.one().d or Decimal(0.0)

    # Get the total amount of fees people have paid for being in debt
    @classmethod
    def fees(cls, start=None, end=None):
        r = DBSession.query(func.sum((cls.amount / (1-cls.discount)) - cls.amount).label('f'))\
                        .join(event.Event)\
                        .filter(cls.discount < 0)\
                        .filter(event.Event.deleted==False)

        if start:
            r = r.filter(event.Event.timestamp>=start)
        if end:
            r = r.filter(event.Event.timestamp<end)

        return r.one().f or Decimal(0.0)

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
                        .filter(event.Event.deleted==False)\
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


    @classmethod
    def get_transactions_over_time_for_user(cls, user):
        return DBSession.query(cls.amount,
                               cls.type,
                               cls.to_account_virt_id,
                               cls.fr_account_virt_id,
                               event.Event.timestamp)\
                        .join(event.Event)\
                        .filter(event.Event.deleted==False)\
                        .filter(or_(
                                  cls.type=='purchase',
                                  cls.type=='cashdeposit',
                                  cls.type=='ccdeposit',
                                  cls.type=='btcdeposit',
                                  cls.type=='adjustment'
                                ))\
                        .filter(or_(
                            cls.to_account_virt_id == user.id,
                            cls.fr_account_virt_id == user.id,
                            ))\
                        .order_by(event.Event.timestamp)\
                        .all()


    @classmethod
    def get_balances_over_time_for_user(cls, user):
        rows = cls.get_transactions_over_time_for_user(user)
        # We can re-use the global balance calculation code because the query
        # filtered it down to only this user, only now the "global" total
        # positive values (r[2]) and total debt (r[1]) are just this user's
        # balance, so we pull out the right column at each point in time.
        rows = utility.timeseries_balance_total_daily(rows)
        rows = [(r[0],r[2]/100 if r[1]==0 else -r[1]/100) for r in rows]
        return rows

    @classmethod
    def get_days_in_debt_for_user(cls, user):
        rows = cls.get_transactions_over_time_for_user(user)
        days = utility.get_days_on_shame(user, rows)
        return days


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
    return __get_events(self)

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
def __get_events_by_type(cls, event_type):
    q = DBSession.query(event.Event)\
            .join(Transaction)

    if event_type == 'cash':
        q = q.filter(or_(
                      Transaction.to_account_cash_id == account.get_cash_account("chezbetty").id,
                      Transaction.fr_account_cash_id == account.get_cash_account("chezbetty").id))
    elif event_type == 'restock':
        q = q.filter(Transaction.type == 'restock')
    elif event_type == 'emptycash':
        q = q.filter(or_(
                      Transaction.type == 'emptycashbox',
                      Transaction.type == 'emptysafe',
                      Transaction.type == 'emptybitcoin'))
    elif event_type == 'deposit':
        q = q.filter(or_(
                      Transaction.type == 'cashdeposit',
                      Transaction.type == 'ccdeposit',
                      Transaction.type == 'btcdeposit'))
    elif event_type == 'donation':
        q = q.filter(or_(
                      Transaction.type == 'donation',
                      Transaction.type == 'withdrawal'))
    elif event_type == 'reimbursement':
        q = q.filter(Transaction.type == 'reimbursement')

    q = q.filter(event.Event.deleted==False)\
         .order_by(desc(event.Event.timestamp))
    return q
event.Event.get_events_by_type = __get_events_by_type

# This is in a stupid place due to circular input problems
@classmethod
@limitable_all
def __get_events_by_cashaccount(cls, account_id):
    q = DBSession.query(event.Event)\
            .join(Transaction)\
            .filter(or_(
                      Transaction.to_account_cash_id == account_id,
                      Transaction.fr_account_cash_id == account_id))\
            .filter(event.Event.deleted==False)\
            .order_by(desc(event.Event.timestamp))
    return q
event.Event.get_events_by_cashaccount = __get_events_by_cashaccount

# This is in a stupid place due to circular input problems
@classmethod
def __get_deadbeats(cls):
    deadbeats = DBSession.query(user.User)\
            .filter(user.User.enabled==True)\
            .filter(user.User.archived==False)\
            .filter(user.User.balance <= -5)\
            .all()

    # Only get users between 0 and -5 if they have been in debt for a week or
    # more.
    iffy_users = DBSession.query(user.User)\
            .filter(user.User.enabled==True)\
            .filter(user.User.archived==False)\
            .filter(user.User.balance < 0)\
            .filter(user.User.balance > -5)\
            .all()
    for u in iffy_users:
        days = Transaction.get_days_in_debt_for_user(u)
        if days >= 7:
            deadbeats.append(u)

    return deadbeats
user.User.get_deadbeats = __get_deadbeats

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

# This is in a stupid place due to circular input problems
@property
def __lifetime_fees(self):
    return object_session(self).query(func.sum((Purchase.amount / (1-Purchase.discount)) - Purchase.amount).label("f"))\
            .join(event.Event)\
            .filter(Purchase.fr_account_virt_id == self.id)\
            .filter(Purchase.discount < 0)\
            .filter(event.Event.type == 'purchase')\
            .filter(event.Event.deleted==False).one().f or Decimal(0.0)
user.User.lifetime_fees = __lifetime_fees

# This is in a stupid place due to circular input problems
@property
def __lifetime_discounts(self):
    return object_session(self).query(func.sum((Purchase.amount / (1-Purchase.discount)) - Purchase.amount).label("f"))\
            .join(event.Event)\
            .filter(Purchase.fr_account_virt_id == self.id)\
            .filter(Purchase.discount > 0)\
            .filter(event.Event.type == 'purchase')\
            .filter(event.Event.deleted==False).one().f or Decimal(0.0)
user.User.lifetime_discounts = __lifetime_discounts

# This is in a stupid place due to circular input problems
@property
def __number_of_purchases(self):
    return object_session(self).query(func.count(Purchase.id).label("c"))\
            .join(event.Event)\
            .filter(Purchase.fr_account_virt_id == self.id)\
            .filter(event.Event.type == 'purchase')\
            .filter(event.Event.deleted==False).one().c or 0
user.User.number_of_purchases = __number_of_purchases

@property
def __relevant_cash_deposits(self):
    # Get the cashbox empty before this one
    previous_cb_empty = object_session(self).query(event.Event)\
            .filter(event.Event.type == 'emptycashbox')\
            .filter(event.Event.timestamp < self.timestamp)\
            .filter(event.Event.deleted == False)\
            .order_by(desc(event.Event.timestamp))\
            .first()

    # Now get all cash deposits between that cash box empty and this one
    q = object_session(self).query(event.Deposit)\
            .filter(event.Event.timestamp < self.timestamp)\
            .order_by(asc(event.Event.timestamp))

    if previous_cb_empty:
        q = q.filter(event.Event.timestamp >= previous_cb_empty.timestamp)

    return q.all()
event.EmptyCashBox.relevant_cash_deposits = __relevant_cash_deposits

################################################################################
## Related Classes
################################################################################

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

    def __init__(self, event, global_cost, reimbursee=None):
        chezbetty_v = account.get_virt_account("chezbetty")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, None, chezbetty_c, reimbursee, Decimal(0.0))
        self.amount_restock_cost = global_cost


class Inventory(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'inventory'}
    def __init__(self, event):
        chezbetty_v = account.get_virt_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, None, None, None, Decimal(0.0))


class EmptyCashBox(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'emptycashbox'}
    def __init__(self, event):
        cashbox_c = account.get_cash_account("cashbox")
        amount = cashbox_c.balance
        safe_c = account.get_cash_account("safe")
        Transaction.__init__(self, event, None, None, cashbox_c, safe_c, amount)


class EmptySafe(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'emptysafe'}
    def __init__(self, event, amount):
        safe_c = account.get_cash_account("safe")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, None, None, safe_c, chezbetty_c, amount)


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
    def __init__(self, event, amount, donator=None):
        chezbetty_v = account.get_virt_account("chezbetty")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, None, chezbetty_v, donator, chezbetty_c, amount)


class Withdrawal(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'withdrawal'}
    def __init__(self, event, amount, reimbursee):
        chezbetty_v = account.get_virt_account("chezbetty")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, None, chezbetty_c, reimbursee, amount)


class Reimbursement(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'reimbursement'}
    def __init__(self, event, amount, reimbursee):
        Transaction.__init__(self, event, None, None, reimbursee, None, amount)


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



