from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from .models import *

@view_config(route_name='home', renderer='templates/home.jinja2')
def my_view(request):
    return {'one': "fuck", 'project': 'chezbetty', 'name':'fuck'}

# /user/<swipe>/umid/uniqname>/json
@view_config(route_name="user_json", renderer="json")
def user_json(request):
    return {"id":1, "uniqname":"zakir", "umid":"95951361", "balance":10.00}

# /item/<barcode>/json
def lookup_item(route_name="item_json", renderer="json")
    return {"id":1, "price": 10.00, "name": "a goddamn granola bar", "in_stock": 10, "in_storage": 30}

