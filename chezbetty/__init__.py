from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from sqlalchemy import engine_from_config

from .models.model import *
from .models.user import LDAPLookup, groupfinder, get_user, User
from .btc import Bitcoin

def main(global_config, **settings):
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    Base.metadata.bind = engine
    config = Configurator(settings=settings,
                          root_factory="chezbetty.models.model.RootFactory")

    def debug(request):
        if 'debugging' in request.registry.settings:
            if not int(request.registry.settings['debugging']):
                return False
        return True

    config.add_request_method(debug, reify=True)

    LDAPLookup.PASSWORD = config.registry.settings["ldap.password"]
    LDAPLookup.USERNAME = config.registry.settings["ldap.username"]
    LDAPLookup.SERVER = config.registry.settings["ldap.server"]

    Bitcoin.COINBASE_API_KEY = config.registry.settings["bitcoin.coinbase_api_key"]
    Bitcoin.COINBASE_API_SECRET = config.registry.settings["bitcoin.coinbase_api_secret"]
    Bitcoin.HOSTNAME = config.registry.settings["chezbetty.host"]

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

    config.add_route('items',            '/items')
    config.add_route('item',             '/item/{barcode}/json')
    config.add_route('item_request',     '/item/request')
    config.add_route('item_request_new', '/item/request/new')

    config.add_route('shame', '/shame')
    config.add_route('user',  '/user/{umid}')

    config.add_route('purchase_new', '/purchase/new')
    config.add_route('purchase',     '/purchase/{umid}')

    config.add_route('deposit_new', '/deposit/new')
    config.add_route('deposit',     '/deposit/{umid}')

    config.add_route('btc_deposit', '/bitcoin/deposit/{umid}/{auth_key}')
    config.add_route('btc_check',   '/bitcoin/check/{addr}')

    config.add_route('event',      '/event/{event_id}')
    config.add_route('event_undo', '/event/undo/{umid}/{event_id}')


    # ADMIN
    config.add_route('admin_index',     '/admin')
    config.add_route('admin_demo',      '/admin/demo/{state}')
    config.add_route('admin_keyboard',  '/admin/keyboard/{state}')

    config.add_route('admin_item_barcode_json', '/admin/item/{barcode}/json')
    config.add_route('admin_restock',           '/admin/restock')
    config.add_route('admin_restock_submit',    '/admin/restock/submit')

    config.add_route('admin_items_add',         '/admin/items/add')
    config.add_route('admin_items_add_submit',  '/admin/items/add/submit')
    config.add_route('admin_items_edit',        '/admin/items/edit')
    config.add_route('admin_items_edit_submit', '/admin/items/edit/submit')
    config.add_route('admin_item_edit_submit',  '/admin/item/edit/submit')
    config.add_route('admin_item_edit',         '/admin/item/edit/{item_id}')
    config.add_route('admin_item_barcode_pdf', '/admin/item/barcode/{item_id}.pdf')

    config.add_route('admin_boxes_add',         '/admin/boxes/add')
    config.add_route('admin_boxes_add_submit',  '/admin/boxes/add/submit')
    config.add_route('admin_boxes_edit',        '/admin/boxes/edit')
    config.add_route('admin_boxes_edit_submit', '/admin/boxes/edit/submit')
    config.add_route('admin_box_edit_submit',   '/admin/box/edit/submit')
    config.add_route('admin_box_edit',          '/admin/box/edit/{box_id}')

    config.add_route('admin_vendors_edit',        '/admin/vendors/edit')
    config.add_route('admin_vendors_edit_submit', '/admin/vendors/edit/submit')

    config.add_route('admin_inventory',        '/admin/inventory')
    config.add_route('admin_inventory_submit', '/admin/inventory/submit')

    config.add_route('admin_users_edit',               '/admin/users/edit')
    config.add_route('admin_users_edit_submit',        '/admin/users/edit/submit')
    config.add_route('admin_users_email',              '/admin/users/email')
    config.add_route('admin_users_email_deadbeats',    '/admin/users/email/deadbeats')
    config.add_route('admin_users_email_all',          '/admin/users/email/all')
    config.add_route('admin_user_balance_edit',        '/admin/user/balance/edit')
    config.add_route('admin_user_balance_edit_submit', '/admin/user/balance/edit/submit')

    config.add_route('admin_cash_reconcile',         '/admin/cash/reconcile')
    config.add_route('admin_cash_reconcile_submit',  '/admin/cash/reconcile/submit')
    config.add_route('admin_cash_reconcile_success', '/admin/cash/reconcile/success')
    config.add_route('admin_cash_donation',          '/admin/cash/donation')
    config.add_route('admin_cash_donation_submit',   '/admin/cash/donation/submit')
    config.add_route('admin_cash_withdrawal',        '/admin/cash/withdrawal')
    config.add_route('admin_cash_withdrawal_submit', '/admin/cash/withdrawal/submit')
    config.add_route('admin_cash_adjustment',        '/admin/cash/adjustment')
    config.add_route('admin_cash_adjustment_submit', '/admin/cash/adjustment/submit')

    config.add_route('admin_btc_reconcile',        '/admin/btc/reconcile')
    config.add_route('admin_btc_reconcile_submit', '/admin/btc/reconcile/submit')

    config.add_route('admin_events',         '/admin/events')
    config.add_route('admin_events_deleted', '/admin/events/deleted')
    config.add_route('admin_event_upload',   '/admin/event/upload')
    config.add_route('admin_event',          '/admin/event/{event_id}')
    config.add_route('admin_event_undo',     '/admin/event/undo/{event_id}')
    config.add_route('admin_event_receipt',  '/admin/event/receipt/{receipt_id}.pdf')

    config.add_route('admin_password_edit',        '/admin/password/edit')
    config.add_route('admin_password_edit_submit', '/admin/password/edit/submit')

    config.add_route('admin_shopping_list', '/admin/shopping')

    config.add_route('admin_requests',        '/admin/requests')
    config.add_route('admin_requests_delete', '/admin/request/delete/{request_id}')

    config.add_route('admin_announcements_edit',        '/admin/announcements/edit')
    config.add_route('admin_announcements_edit_submit', '/admin/announcements/edit/submit')



    config.add_route('admin_data_items_day_json', '/admin/data/items/day')
    config.add_route('admin_data_sales_day_json', '/admin/data/sales/day')


    config.add_route('login',  '/login')
    config.add_route('logout', '/logout')
    config.add_request_method(get_user, "user", reify=True)

    config.scan(".views")
    config.scan(".views_admin")
    config.scan(".views_data")

    return config.make_wsgi_app()
