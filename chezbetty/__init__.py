from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from sqlalchemy import engine_from_config

from .models.model import *
from .models.user import LDAPLookup, groupfinder

def main(global_config, **settings):
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    Base.metadata.bind = engine
    config = Configurator(settings=settings)
    
    LDAPLookup.PASSWORD = config.registry.settings["ldap.password"]
    LDAPLookup.USERNAME = config.registry.settings["ldap.username"]
    LDAPLookup.SERVER = config.registry.settings["ldap.server"]
    
    authn_policy = AuthTktAuthenticationPolicy(
           config.registry.settings["auth.secret"],
           callback=groupfinder, hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    
    config.include('pyramid_jinja2')
    config.include('pyramid_beaker')
    
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('index', '/')

    config.add_route('about', '/about')

    config.add_route('items', '/items')
    config.add_route('item', '/item/{barcode}/json')

    config.add_route('users', '/users')
    config.add_route('user', '/user/{umid}')

    config.add_route('purchase_new', '/purchase/new')
    config.add_route('purchase', '/purchase/{umid}')

    config.add_route('deposit_new', '/deposit/new')
    config.add_route('deposit', '/deposit/{umid}')

    config.add_route('transaction', '/transaction/{transaction_id}')

    # ADMIN
    config.add_route('admin_login', '/admin')
    config.add_route('admin_index', '/admin/index')
    config.add_route('admin_edit_items', '/admin/edit/items')
    config.add_route('admin_inventory', '/admin/inventory')

    config.scan(".views")

    return config.make_wsgi_app()
