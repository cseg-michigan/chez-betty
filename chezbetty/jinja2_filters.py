
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
