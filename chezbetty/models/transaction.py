from .model import *
from . import account
from . import event
from . import item
from chezbetty import utility


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
                       "deposit",       # null         -> user_account.     null      -> cashbox.
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


@property
def __transactions(self):
    return object_session(self).query(Transaction)\
            .join(event.Event)\
            .filter(or_(
                    Transaction.to_account_virt_id == self.id,
                    Transaction.fr_account_virt_id == self.id,
                    Transaction.to_account_cash_id == self.id,
                    Transaction.fr_account_cash_id == self.id))\
            .filter(event.Event.deleted==False).all()
account.Account.transactions = __transactions

# This is in a stupid place due to circular input problems
@property
def __events(self):
    return object_session(self).query(event.Event)\
            .join(Transaction)\
            .filter(or_(
                    Transaction.to_account_virt_id == self.id,
                    Transaction.fr_account_virt_id == self.id,
                    Transaction.to_account_cash_id == self.id,
                    Transaction.fr_account_cash_id == self.id))\
            .filter(event.Event.deleted==False).all()
account.Account.events = __events

class Purchase(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'purchase'}
    def __init__(self, event, user):
        chezbetty_v = account.get_virt_account("chezbetty")
        Transaction.__init__(self, event, user, chezbetty_v, None, None, Decimal(0.0))


class Deposit(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'deposit'}
    def __init__(self, event, user, amount):
        cashbox_c = account.get_cash_account("cashbox")
        Transaction.__init__(self, event, None, user, None, cashbox_c, amount)

    @classmethod
    def deposits_by_period(cls, period):
        r = DBSession.query(cls.amount.label('summable'), event.Event.timestamp)\
                     .join(event.Event)\
                     .order_by(event.Event.timestamp).all()
        return utility.group(r, period)


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
        return DBSession.query(cls)\
                        .filter(cls.address == address)\
                        .filter(cls.event.deleted==False).one()


class Adjustment(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'adjustment'}

    def __init__(self, event, user, amount):
        chezbetty_v = account.get_virt_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, user, None, None, amount)


class Restock(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'restock'}
    def __init__(self, event):
        chezbetty_v = account.get_virt_account("chezbetty")
        chezbetty_c = account.get_cash_account("chezbetty")
        Transaction.__init__(self, event, chezbetty_v, None, chezbetty_c, None, Decimal(0.0))


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
                                  "inventorylineitem",
                                  name="subtransaction_type"), nullable=False)
    item_id         = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity        = Column(Integer, nullable=False)
    wholesale       = Column(Numeric, nullable=False)

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
    def all_item(cls, id):
        return DBSession.query(cls)\
                        .join(Transaction)\
                        .join(event.Event)\
                        .filter(cls.item_id == id)\
                        .filter(event.Event.deleted==False).all()


class PurchaseLineItem(SubTransaction):
    __mapper_args__ = {'polymorphic_identity': 'purchaselineitem'}
    price     = Column(Numeric)
    def __init__(self, transaction, amount, item, quantity, price, wholesale):
        SubTransaction.__init__(self, transaction, amount, item.id, quantity, wholesale)
        self.price = price

    @classmethod
    def quantity_by_period(cls, period):
        r = DBSession.query(cls.quantity.label('summable'), event.Event.timestamp)\
                     .join(Transaction)\
                     .join(event.Event)\
                     .filter(event.Event.deleted==False)\
                     .order_by(event.Event.timestamp).all()
        return utility.group(r, period)

    @classmethod
    def virtual_revenue_by_period(cls, period):
        r = DBSession.query(cls.amount.label('summable'), event.Event.timestamp)\
                     .join(Transaction)\
                     .join(event.Event)\
                     .filter(event.Event.deleted==False)\
                     .order_by(event.Event.timestamp).all()
        return utility.group(r, period)


@property
def __number_sold(self):
    return object_session(self).query(func.sum(PurchaseLineItem.quantity).label('c'))\
                               .join(Transaction)\
                               .join(event.Event)\
                               .filter(PurchaseLineItem.item_id==self.id)\
                               .filter(event.Event.deleted==False).one().c
item.Item.number_sold = __number_sold


class RestockLineItem(SubTransaction):
    __mapper_args__ = {'polymorphic_identity': 'restocklineitem'}
    def __init__(self, transaction, amount, item, quantity, wholesale):
        SubTransaction.__init__(self, transaction, amount, item.id, quantity, wholesale)
        self.quantity = quantity
        self.wholesale = wholesale


class InventoryLineItem(SubTransaction):
    __mapper_args__    = {'polymorphic_identity': 'inventorylineitem'}
    quantity_predicted = synonym(SubTransaction.quantity)
    quantity_counted   = Column(Integer)

    def __init__(self, transaction, amount, item, quantity_predicted, quantity_counted, wholesale):
        SubTransaction.__init__(self, transaction, amount, item.id, quantity_predicted, wholesale)
        self.quantity_counted = quantity_counted



