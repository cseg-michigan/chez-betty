from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from sqlalchemy import engine_from_config

from .models.model import *
from .models.user import LDAPLookup, groupfinder, get_user
from .btc import Bitcoin

def main(global_config, **settings):
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    Base.metadata.bind = engine
    config = Configurator(settings=settings, root_factory="chezbetty.models.model.RootFactory")

    LDAPLookup.PASSWORD = config.registry.settings["ldap.password"]
    LDAPLookup.USERNAME = config.registry.settings["ldap.username"]
    LDAPLookup.SERVER = config.registry.settings["ldap.server"]

    Bitcoin.COINBASE_API_KEY = config.registry.settings["bitcoin.coinbase_api_key"]
    Bitcoin.COINBASE_API_SECRET = config.registry.settings["bitcoin.coinbase_api_secret"]

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

    config.add_route('btc_deposit', '/bitcoin/deposit/{guid}')
    config.add_route('btc_check', '/bitcoin/check/{addr}')

    config.add_route('event', '/event/{event_id}')
    config.add_route('event_undo', '/event/undo/{umid}/{event_id}')

    # ADMIN
    config.add_route('admin_index', '/admin')
    config.add_route('admin_demo', '/admin/demo/{state}')
    config.add_route('admin_item_barcode_json', '/admin/item/{barcode}/json')
    config.add_route('admin_restock', '/admin/restock')
    config.add_route('admin_restock_submit', '/admin/restock/submit')

    config.add_route('admin_items_add',         '/admin/items/add')
    config.add_route('admin_items_add_submit',  '/admin/items/add/submit')
    config.add_route('admin_items_edit',        '/admin/items/edit')
    config.add_route('admin_items_edit_submit', '/admin/items/edit/submit')
    config.add_route('admin_item_edit_submit',  '/admin/item/edit/submit')
    config.add_route('admin_item_edit',         '/admin/item/edit/{item_id}')

    config.add_route('admin_vendors_edit',        '/admin/vendors/edit')
    config.add_route('admin_vendors_edit_submit', '/admin/vendors/edit/submit')

    config.add_route('admin_inventory', '/admin/inventory')
    config.add_route('admin_inventory_submit', '/admin/inventory/submit')

    config.add_route('admin_edit_users', '/admin/edit/users')
    config.add_route('admin_edit_users_submit', '/admin/edit/users/submit')
    config.add_route('admin_edit_balance', '/admin/edit/balance')
    config.add_route('admin_edit_balance_submit', '/admin/edit/balance/submit')

    config.add_route('admin_cash_reconcile', '/admin/cash/reconcile')
    config.add_route('admin_cash_reconcile_submit', '/admin/cash/reconcile/submit')
    config.add_route('admin_cash_reconcile_success', '/admin/cash/reconcile/success')
    config.add_route('admin_cash_donation', '/admin/cash/donation')
    config.add_route('admin_cash_donation_submit', '/admin/cash/donation/submit')
    config.add_route('admin_cash_withdrawal', '/admin/cash/withdrawal')
    config.add_route('admin_cash_withdrawal_submit', '/admin/cash/withdrawal/submit')
    config.add_route('admin_cash_adjustment', '/admin/cash/adjustment')
    config.add_route('admin_cash_adjustment_submit', '/admin/cash/adjustment/submit')

    config.add_route('admin_transactions', '/admin/transactions')
    config.add_route('admin_event', '/admin/event/{event_id}')

    config.add_route('admin_edit_password', '/admin/edit/password')
    config.add_route('admin_edit_password_submit', '/admin/edit/password/submit')


    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_request_method(get_user, "user", reify=True)

    config.scan(".views")
    config.scan(".views_admin")

    return config.make_wsgi_app()
