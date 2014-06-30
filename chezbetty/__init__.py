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
    config = Configurator(settings=settings, root_factory="chezbetty.models.model.RootFactory")
    
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

    config.add_route('shame', '/shame')
    config.add_route('user', '/user/{umid}')

    config.add_route('purchase_new', '/purchase/new')
    config.add_route('purchase', '/purchase/{umid}')

    config.add_route('deposit_new', '/deposit/new')
    config.add_route('deposit', '/deposit/{umid}')

    config.add_route('transaction', '/transaction/{transaction_id}')
    config.add_route('transaction_undo', '/transaction/undo/{umid}/{transaction_id}')

    # ADMIN
    config.add_route('admin_index', '/admin')
    config.add_route('admin_item_barcode_json', '/admin/item/{barcode}/json')
    config.add_route('admin_restock', '/admin/restock')
    config.add_route('admin_restock_submit', '/admin/restock/submit')
    config.add_route('admin_add_items', '/admin/add/items')
    config.add_route('admin_add_items_submit', '/admin/add/items/submit')
    config.add_route('admin_edit_items', '/admin/edit/items')
    config.add_route('admin_edit_items_submit', '/admin/edit/items/submit')
    config.add_route('admin_inventory', '/admin/inventory')
    config.add_route('admin_inventory_submit', '/admin/inventory/submit')
    config.add_route('admin_edit_users', '/admin/edit/users')
    config.add_route('admin_edit_users_submit', '/admin/edit/users/submit')
    config.add_route('admin_edit_balance', '/admin/edit/balance')
    config.add_route('admin_edit_balance_submit', '/admin/edit/balance/submit')
    config.add_route('admin_cash_reconcile', '/admin/cash/reconcile')
    config.add_route('admin_cash_reconcile_submit', '/admin/cash/reconcile/submit')
    config.add_route('admin_cash_reconcile_success', '/admin/cash/reconcile/success')
    config.add_route('admin_transactions', '/admin/transactions')
    config.add_route('admin_view_transaction', '/admin/transactions/{id}')

    config.add_route('login', '/login')
    config.add_route('logout', '/logout')

    config.scan(".views")

    return config.make_wsgi_app()
