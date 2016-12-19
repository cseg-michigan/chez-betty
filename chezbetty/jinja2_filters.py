from .models import box
from .models import item
from .models import user
from .models import account
from .models import pool

import arrow
import jinja2

from sh import ErrorReturnCode, git

def format_currency(value):
	try:
		p = float(value)
	except ValueError:
		return value
	# We stored currency as floats, avoid the -$0.00 case
	if p <= -0.01:
		 return '<span class="negative">-${:,.2f}</span>'.format(p*-1.0)
	else:
		return '<span class="positive">${:,.2f}</span>'.format(value)

def format_debt(value):
	try:
		p = float(value)
	except ValueError:
		return value
	# We stored currency as floats, avoid the -$0.00 case
	if p <= -0.01:
		 return '<span class="negative">${:,.2f}</span>'.format(p*-1.0)
	print("WARN: format_debt expects a negative value")
	return format_currency(value)

# Convert UTC datetime object from the database to the local time
# of the Chez Betty instance.
# TODO: pass the timezone in to this somehow, but for now we just go
# with eastern. Sorry.
def pretty_date(datetime_obj):
	eastern = arrow.get(datetime_obj).to('US/Eastern')
	eastern_date = eastern.format('MMM D, YYYY')
	eastern_time = eastern.format('hh:mm A')
	return '<span class="prettydate">{} at {}</span>'.format(eastern_date, eastern_time)

def human_date(datetime_obj):
	eastern = arrow.get(datetime_obj).to('US/Eastern')
	return eastern.humanize()

# Shorten a string to l length
def shorten(s, l):
	if l == 0:
		return s
	elif len(s) <= l:
		return s
	else:
		return s[0:l-1] + '…'

def make_link(obj, str_len=0):
	if obj is None:
		return ''
	elif type(obj) is box.Box:
		return '<a href="/admin/box/edit/{}">{}</a>'.format(obj.id, shorten(obj.name, str_len))
	elif type(obj) is item.Item:
		return '<a href="/admin/item/edit/{}">{}</a>'.format(obj.id, shorten(obj.name, str_len))
	elif type(obj) is user.User:
		return '<a href="/admin/user/{}">{}</a>'.format(obj.id, shorten(obj.name, str_len))
	elif type(obj) is pool.Pool:
		return '<a href="/admin/pool/{}">{}</a>'.format(obj.id, shorten(obj.name, str_len))
	else:
		return obj.name

def make_user_link(obj, str_len=0):
	if type(obj) is pool.Pool:
		return '<a href="/user/pool/{}">{}</a>'.format(obj.id, shorten(obj.name, str_len))
	else:
		return obj.name

def add_git_version(s):
	try:
		return ' '+git.describe('--tags').strip()
	except ErrorReturnCode:
		pass

