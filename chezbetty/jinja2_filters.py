from .models import box
from .models import item
from .models import user
from .models import account
from .models import pool

def format_currency(value):
	try:
		p = float(value)
	except ValueError:
		return value
	if p < 0:
		 return '<span class="negative">-${:,.2f}</span>'.format(p*-1.0)
	else:
		return '<span class="positive">${:,.2f}</span>'.format(value)

# This should be done client side
def pretty_date(datetime_obj):
	return '<span class="date">{}</span>'.format(datetime_obj.strftime('%m/%d/%Y %I:%M:%S %p UTC'))

# Shorten a string to l length
def shorten(s, l):
	if l == 0:
		return s
	elif len(s) <= l:
		return s
	else:
		return s[0:l-1] + '…'

def make_link(obj, str_len=0):
	if type(obj) is box.Box:
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
