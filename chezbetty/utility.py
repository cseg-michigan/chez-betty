import datetime
import itertools
import qrcode
import qrcode.image.svg

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

# TODO: Should probably send mail 'from' our actual server and have a local MTA
# that forwards mails to this alias
def send_email(TO, SUBJECT, body, FROM='chez-betty@umich.edu'):
    settings = get_current_registry().settings

    if 'smtp.host' in settings:
        sm = smtplib.SMTP(host=settings['smtp.host'])
    else:
        sm = smtplib.SMTP()
        sm.connect()
    if 'smtp.username' in settings:
        sm.login(settings['smtp.username'], settings['smtp.password'])

    msg = MIMEMultipart()
    msg['Subject'] = SUBJECT
    msg['From'] = FROM
    msg['To'] = TO
    msg.attach(MIMEText(body, 'html'))

    if 'debugging' in settings:
        print(msg.as_string())
        if 'debugging_send_email' in settings and settings['debugging_send_email'] == 'true':
            try:
                msg.replace_header('To', settings['debugging_send_email_to'])
                print("DEBUG: e-mail destination overidden to {}".format(msg['To']))
            except KeyError: pass
            send_to = msg['To'].split(', ')
            sm.sendmail(FROM, send_to, msg.as_string())
        else:
            print("Mail suppressed due to debug settings")
    else:
        send_to = msg['To'].split(', ')
        sm.sendmail(FROM, send_to, msg.as_string())
    sm.quit()


def user_password_reset(user):
    password = user.random_password()
    send_email(TO=user.uniqname+'@umich.edu',
               SUBJECT='Chez Betty Login',
               body=render('templates/admin/email_password.jinja2', {'user': user, 'password': password}))


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



