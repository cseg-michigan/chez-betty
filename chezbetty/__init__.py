from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import *

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application."""
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    config = Configurator(settings=settings)
    config.include('pyramid_jinja2')
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('about', '/about.html')

    config.add_route('items', '/items.html')
    config.add_route('item', '/item/{barcode}')

    config.add_route('users', '/users.html')
    config.add_route('user', '/user/{umid}')

    config.add_route('purchase', '/purchase.html')
    config.add_route('purchase_new', '/purchase/{umid}')

    config.add_route('deposit', '/deposit.html')
    config.add_route('deposit_new', '/deposit/new')

    # Old testing / startup stubs
    config.add_route('home', '/')
    config.add_route('user_json', '/user/{uid}/json')
    config.add_route('item_json', '/item/{iid}/json')

    config.scan(".views")

    return config.make_wsgi_app()
