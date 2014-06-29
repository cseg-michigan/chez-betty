import time

def format_currency(value):
	p = float(value)
	if p < 0:
		 return '<span class="negative">-${:,.2f}</span>'.format(p*-1.0)
	else:
		return '<span class="positive">${:,.2f}</span>'.format(value)

def pretty_date(datetime_obj):
	return datetime_obj.strftime('%B %d, %Y at %I:%M%p')
