from .models import box
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

def admin_item(item):
	return '<a href="/admin/item/edit/{}">{}</a>'.format(item.id, item.name)

def admin_user(user):
	return '<a href="/user/{}">{}</a>'.format(user.umid, user.name)

def admin_account(account):
	try:
		return admin_user(account)
	except AttributeError:
		return '{}'.format(account.name)

def make_link(obj):
	if type(obj) is box.Box:
		return '<a href="/admin/box/edit/{}">{}</a>'.format(obj.id, obj.name)
