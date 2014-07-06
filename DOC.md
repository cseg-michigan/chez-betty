Chez Betty Documentation
========================

Chez Betty is, at its core, a transaction management system. Every action
performed by a user or admin is recorded as an event with one or more
associated transactions. Transactions move money between accounts, or, in
some cases, from outside of the system to an account or from an account
to outside of the system. Each transaction is labeled with a transaction
type, allowing the system to track where money is going or coming from.

Chez Betty has two types of accounts: cash and virtual. Cash accounts
hold actual, physical money. Virtual accounts hold money as it flows through
Chez Betty, but no actual USD changes hands. This two-account system
allows for natural support of the deposit based model. By separating cash
from internal transactions, we can easily track how much we have received
in deposits as well as how much users should be debited for purchases.

There are five accounts in the Chez Betty system:

| Virtual Acocunts   | Description                                        |
| ------------------ | -------------------------------------------------- |
| chezbetty          | General account                                    |
| users              | A series of accounts that hold each user's balance |

| Cash Acocunts      | Description                                        |
| ------------------ | -------------------------------------------------- |
| chezbetty          | Chez Betty bank account                            |
| cashbox            | How much cash there should be in the dropbox       |
| btcbox             | How much cash we should be able to convert our bitcoins to |

To demonstrate how the accounts work, take a user deposit as an example. Say
Bob wants to deposit $5 into his account. He puts $5 in the drop box and
enters $5 into the deposit page. This creates a transaction:

    Transaction:
      amount: 5.00
      type:   deposit
      virtual accounts:
        from: null
        to:   bob
      cash accounts
        from: null
        to:   cashbox

At this point Bob's user account has $5.00 in it and we record that there
should be $5 cash in the dropbox by putting money in the cashbox account.

Now, of course, we don't actually know how much money is in the dropbox for
sure. Therefore, we must reconcile the cashbox actual versus what we think
should be in there. We do this by telling Chez Betty how much was actually
in the box. Say Bob wasn't very nice and only put $4 in the drop box.
Reconciling this creates two transactions:

    Transaction 1:
      amount: 1.00
      type:   lost
      virtual accounts:
      	from: null
      	to:   null
      cash accounts:
        from: cashbox
        to:   null

    Transaction 2:
      amount: 4.00
      type:   emptycashbox
      virtual accounts:
      	from: null
      	to:   null
      cash accounts:
        from: cashbox
        to:   chezbetty

Transaction 1 reconciles the cashbox's expected value and what was actually
in it. To keep the accounting correct, we must move $1.00 from the cashbox
account to null and label it "lost". Then, we move the actual cashbox
contents to the chezbetty cash account.


