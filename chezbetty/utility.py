import datetime
from decimal import Decimal
import itertools
import qrcode
import qrcode.image.svg
import stripe
import traceback

from pyramid.renderers import render
from pyramid.threadlocal import get_current_registry

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import pytz

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase

def _send_email(msg, FROM):
    settings = get_current_registry().settings

    if 'debugging' in settings and bool(int(settings['debugging'])):
        if 'debugging_send_email' not in settings or settings['debugging_send_email'] != 'true':
            print("Mail suppressed due to debug settings")
            return

    if 'smtp.host' in settings:
        sm = smtplib.SMTP(host=settings['smtp.host'])
    else:
        sm = smtplib.SMTP()
        sm.connect()
    if 'smtp.username' in settings:
        sm.login(settings['smtp.username'], settings['smtp.password'])

    def gen_sendto(msg):
        send_to = []
        if 'To' in msg:
            send_to += msg['To'].split(', ')
        if 'CC' in msg:
            send_to += msg['CC'].split(', ')
        if 'BCC' in msg:
            send_to += msg['BCC'].split(', ')
        return send_to


    if 'debugging' in settings and bool(int(settings['debugging'])):
        if 'debugging_send_email' in settings and settings['debugging_send_email'] == 'true':
            try:
                msg.replace_header('To', settings['debugging_send_email_to'])
                print("DEBUG: e-mail TO overidden to {}".format(msg['To']))
            except KeyError: pass
            try:
                msg.replace_header('CC', settings['debugging_send_email_to'])
                print("DEBUG: e-mail CC overidden to {}".format(msg['CC']))
            except KeyError: pass
            try:
                msg.replace_header('BCC', settings['debugging_send_email_to'])
                print("DEBUG: e-mail BCC overidden to {}".format(msg['BCC']))
            except KeyError: pass
            send_to = gen_sendto(msg)
            sm.sendmail(FROM, send_to, msg.as_string())
    else:
        send_to = gen_sendto(msg)
        sm.sendmail(FROM, send_to, msg.as_string())
    sm.quit()


def send_email(TO, SUBJECT, body,
        FROM='chez-betty@umich.edu',
        encoding='html',
        ):
    msg = MIMEMultipart()
    msg['Subject'] = SUBJECT
    msg['From'] = FROM
    msg['To'] = TO
    if encoding == 'text':
        msg.attach(MIMEText(body))
    else:
        msg.attach(MIMEText(body, encoding))
    print(msg.as_string())
    _send_email(msg, FROM)


def send_bcc_email(BCC, SUBJECT, body,
        FROM='chez-betty@umich.edu',
        encoding='html',
        ):
    msg = MIMEMultipart()
    msg['Subject'] = SUBJECT
    msg['From'] = FROM
    msg['BCC'] = BCC
    if encoding == 'text':
        msg.attach(MIMEText(body))
    else:
        msg.attach(MIMEText(body, encoding))
    print(msg.as_string())
    _send_email(msg, FROM)


def user_password_reset(user):
    password = user.random_password()
    send_email(TO=user.uniqname+'@umich.edu',
               SUBJECT='Chez Betty Login',
               body=render('templates/admin/email_password.jinja2', {'user': user, 'password': password}))

def notify_pool_out_of_credit(owner, pool):
    send_email(
            TO=owner.uniqname+'@umich.edu',
            SUBJECT='[Chez Betty] Credit limit reached for {} pool'.format(pool.name),
            body=render('templates/admin/email_pool_credit_limit.jinja2',
                {'pool': pool, 'owner': owner})
            )


def string_to_qrcode(s):
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(s, image_factory=factory, box_size=14,
        version=4,
        border=0)
    img.save('/dev/null')   # This is needed, I swear.
    return ET.tostring(img._img).decode('utf-8')

class InvalidGroupPeriod(Exception):
    pass

def group(rows, period='day'):

    def fix_timezone(i):
        return i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=pytz.timezone('America/Detroit'))
    def group_month(i):
        dt = fix_timezone(i)
        return datetime.date(dt.year, dt.month, 1)
    def group_year(i):
        dt = fix_timezone(i)
        return datetime.date(dt.year, 1, 1)

    if period == 'day':
        group_function = lambda i: fix_timezone(i).date()
    elif period == 'month':
        group_function = group_month
    elif period == 'year':
        group_function = group_year
    elif period == 'month_each':
        group_function = lambda i: fix_timezone(i).month
    elif period == 'day_each':
        group_function = lambda i: fix_timezone(i).day
    elif period == 'weekday_each':
        group_function = lambda i: fix_timezone(i).weekday()
    elif period == 'hour_each':
        group_function = lambda i: fix_timezone(i).hour
    else:
        raise(InvalidGroupPeriod(period))


    if 'each' in period:
        # If we are grouping in a very finite set of bins (like days of the
        # week), then use a hash map instead of a list as a return
        sums = {}
        for row in rows:
            item_period = group_function(row)
            if item_period not in sums:
                sums[item_period] = 0
            sums[item_period] += row.summable

    else:
        # If we are grouping in a long list of things (days over some range)
        # then a list is better.
        sums = []
        for (item_period, items) in itertools.groupby(rows, group_function):
            total = 0
            for item in items:
                total += item.summable
            sums.append((item_period, total))

    return sums

# Returns an array of tuples where the first item in the tuple is a millisecond
# timestamp and the second item is the total number of things so far.
def timeseries_cumulative(rows):
    total = 0
    out = []

    for r in rows:
        if len(r) == 1:
            total += 1
        else:
            total += r[1]
        t = round(r[0].replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
        out.append((t, total))

    return out

# [(milliseconds, debt, bank_balance, debt/# users in debt), ...]
def timeseries_balance_total_daily(rows):

    # Is debt going away or coming in
    directions = {
        'purchase':   -1, # user balance goes down by amount
        'cashdeposit': 1, # user balance goes up by amount
        'ccdeposit':   1,
        'btcdeposit':  1,
        'adjustment':  1
    }

    user_balances = {}
    total_debt = 0
    total_balance = 0
    users_in_debt = 0

    out = []

    for r in rows:
        amount = r[0]
        trtype = r[1]
        to_uid = r[2]
        fr_uid = r[3]
        timest = r[4]
        t = timest.timestamp*1000

        # We get the user/pool id from whether we care about where the
        # money came from or went
        if directions[trtype] == -1:
            userid = fr_uid
        else:
            userid = to_uid

        # Calculate the new balance so we can compare it to the old
        old_balance = user_balances.get(userid, 0)
        new_balance = old_balance + (directions[trtype]*amount)
        user_balances[userid] = new_balance

        # Look for swings from in debt to not in debt and vice-versa.
        # This is how we update the running totals of debt and bank holdings.
        if old_balance < 0 and new_balance >= 0:
            # Was in debt, now not
            total_debt -= -1*old_balance
            total_balance += new_balance
            users_in_debt -= 1
        elif old_balance >= 0 and new_balance < 0:
            # Wasn't in debt, now is
            total_balance -= old_balance
            total_debt += -1*new_balance
            users_in_debt += 1
        elif new_balance < 0:
            # still in debt
            total_debt += -1*directions[trtype]*amount
        else:
            # hey, in the black!
            total_balance += directions[trtype]*amount

        # Add to output array
        out.append((t, round(total_debt*100), round(total_balance*100), round((total_debt*100)/users_in_debt)))

    return out

def post_stripe_payment(
        datalayer, # Need to pass as argument to avoid circular import, ugh
        request,
        token,
        amount,
        total_cents,
        account_making_payment,
        account_depositing_into,
        ):
    # See http://stripe.com/docs/tutorials/charges
    stripe.api_key = request.registry.settings['stripe.secret_key']

    charge = (amount + 0.3) / 0.971
    fee = charge - amount
    if total_cents != int(round((amount + fee)*100)):
        print("Stripe total mismatch. total_cents {} != {}".format(
            total_cents, int(round((amount + fee)*100))))
        request.session.flash('Unexpected error processing transaction. Card NOT charged.', 'error')
        return False
    amount = Decimal(amount)

    if amount <= 0.0:
        request.session.flash(
                _('Deposit amount must be greater than $0.00. Card NOT charged.'),
                'error'
                )
        return False

    try:
        charge = stripe.Charge.create(
                amount = total_cents,
                currency="usd",
                source=token,
                description=account_making_payment.uniqname+'@umich.edu'
                )

    except stripe.CardError as e:
        traceback.print_exc()
        request.session.flash('Card error processing transaction. Card NOT charged.', 'error')
        return False
    except stripe.StripeError as e:
        traceback.print_exc()
        request.session.flash('Unexpected error processing transaction. Card NOT charged.', 'error')
        request.session.flash('Please e-mail chezbetty@umich.edu so we can correct this error', 'error')
        return False

    try:
        deposit = datalayer.cc_deposit(
                account_making_payment,
                account_depositing_into,
                amount,
                charge['id'],
                charge['source']['last4'])

        request.session.flash('Deposit added successfully.', 'success')

    except Exception as e:
        traceback.print_exc()
        request.session.flash('A unknown error has occured.', 'error')
        request.session.flash('Your card HAS been charged, but your account HAS NOT been credited.', 'error')
        request.session.flash('Please e-mail chezbetty@umich.edu so we can correct this error', 'error')

    return True

