from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models.model import *
from .models.user import LDAPLookup

def main(global_config, **settings):
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    Base.metadata.bind = engine
    config = Configurator(settings=settings)
    
    print(config.registry.settings)
    LDAPLookup.PASSWORD = config.registry.settings["ldap.password"]
    LDAPLookup.USERNAME = config.registry.settings["ldap.username"]
    LDAPLookup.SERVER = config.registry.settings["ldap.server"]
        
    config.include('pyramid_jinja2')
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('index', '/')

    config.add_route('about', '/about')

    config.add_route('items', '/items')
    config.add_route('item', '/item/{barcode}/json')

    config.add_route('users', '/users')
    config.add_route('user', '/user/{umid}')

    config.add_route('purchase_new', '/purchase')
    config.add_route('purchase', '/purchase/{umid}')

    config.add_route('deposit', '/deposit')
    config.add_route('deposit_new', '/deposit/new')

    # Old testing / startup stubs
    config.add_route('user_json', '/user/{uid}/json')
    config.add_route('item_json', '/item/{iid}/json')

    config.scan(".views")

    return config.make_wsgi_app()
