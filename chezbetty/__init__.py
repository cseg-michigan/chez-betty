from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import engine_from_config

# Import all models so they get auto created if they don't exist
from .models import account
from .models import announcement
from .models import box
from .models import box_item
from .models import box_vendor
from .models import btcdeposit
from .models import event
from .models import item
from .models import item_vendor
from .models import item_tag
from .models import receipt
from .models import request
from .models import transaction
from .models import user
from .models import vendor
from .models import pool
from .models import pool_user
from .models import tag
from .models import tag_relations
from .models.model import *
from .models.user import LDAPLookup, groupfinder, get_user, User
from .btc import Bitcoin

###
### 404
###

def notfound(request):
    request.session.flash('404: Could not find that page.', 'error')
    return HTTPFound(location=request.route_url('index'))

def main(global_config, **settings):
    engine = engine_from_config(settings, 'sqlalchemy.')
    Base.metadata.create_all(engine)
    DBSession.configure(bind=engine)

    Base.metadata.bind = engine
    config = Configurator(settings=settings,
                          root_factory="chezbetty.models.model.RootFactory")
    config.add_translation_dirs('chezbetty:locale/')

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

    config.add_route('index',               '/')

    config.add_route('lang',                '/lang-{code}')

    config.add_route('about',               '/about')
    config.add_route('shame',               '/shame')

    config.add_route('items',               '/items')
    config.add_route('item',                '/item/{barcode}/json')
    config.add_route('item_request',        '/item/request')
    config.add_route('item_request_new',    '/item/request/new')
    config.add_route('item_request_by_id',  '/item/request/by_id/{id}')

    config.add_route('user',                '/profile/{umid}')

    config.add_route('purchase_new',        '/purchase/new')
    config.add_route('purchase',            '/purchase/{umid}')

    config.add_route('deposit_new',         '/deposit/new')
    config.add_route('deposit',             '/deposit/{umid}')
    config.add_route('deposit_edit',        '/deposit/edit/{umid}/{event_id}')
    config.add_route('deposit_edit_submit', '/deposit/edit/submit')

    config.add_route('btc_deposit',         '/bitcoin/deposit/{umid}/{auth_key}')
    config.add_route('btc_check',           '/bitcoin/check/{addr}')

    config.add_route('event',               '/event/{event_id}')
    config.add_route('event_undo',          '/event/undo/{umid}/{event_id}')


    # USER ADMIN
    config.add_route('user_index',                 '/user')

    config.add_route('user_ajax_bool',             '/user/ajax/bool/{object}/{id}/{field}/{state}')

    config.add_route('user_deposit_cc',            '/user/deposit_cc')
    config.add_route('user_deposit_cc_submit',     '/user/deposit_cc/submit')

    config.add_route('user_pools',                 '/user/pools')
    config.add_route('user_pools_new_submit',      '/user/pools/new/submit')
    config.add_route('user_pool',                  '/user/pool/{pool_id}')
    config.add_route('user_pool_addmember_submit', '/user/pool/addmember/submit')


    # ADMIN
    config.add_route('admin_index',             '/admin')

    config.add_route('admin_ajax_bool',         '/admin/ajax/bool/{object}/{id}/{field}/{state}')
    config.add_route('admin_ajax_new',          '/admin/ajax/new/{object}/{arg}')
    config.add_route('admin_ajax_connection',   '/admin/ajax/connection/{object1}/{object2}/{arg1}/{arg2}')

    config.add_route('admin_ajaxed_field',      '/admin/ajax/field/{field}')

    config.add_route('admin_item_barcode_json', '/admin/item/{barcode}/json')
    config.add_route('admin_item_search_json',  '/admin/item/search/{search}/json')
    config.add_route('admin_restock',           '/admin/restock')
    config.add_route('admin_restock_submit',    '/admin/restock/submit')

    config.add_route('admin_items_add',         '/admin/items/add')
    config.add_route('admin_items_add_submit',  '/admin/items/add/submit')
    config.add_route('admin_items_edit',        '/admin/items/edit')
    config.add_route('admin_items_edit_submit', '/admin/items/edit/submit')
    config.add_route('admin_item_edit_submit',  '/admin/item/edit/submit')
    config.add_route('admin_item_edit',         '/admin/item/edit/{item_id}')
    config.add_route('admin_item_barcode_pdf',  '/admin/item/barcode/{item_id}.pdf')
    config.add_route('admin_item_delete',       '/admin/item/delete/{item_id}')

    config.add_route('admin_box_add',           '/admin/box/add')
    config.add_route('admin_box_add_submit',    '/admin/box/add/submit')
    config.add_route('admin_boxes_edit',        '/admin/boxes/edit')
    config.add_route('admin_boxes_edit_submit', '/admin/boxes/edit/submit')
    config.add_route('admin_box_edit_submit',   '/admin/box/edit/submit')
    config.add_route('admin_box_edit',          '/admin/box/edit/{box_id}')
    config.add_route('admin_box_delete',        '/admin/box/delete/{box_id}')

    config.add_route('admin_vendors_edit',        '/admin/vendors/edit')
    config.add_route('admin_vendors_edit_submit', '/admin/vendors/edit/submit')

    config.add_route('admin_inventory',        '/admin/inventory')
    config.add_route('admin_inventory_submit', '/admin/inventory/submit')

    config.add_route('admin_users_edit',               '/admin/users/edit')
    config.add_route('admin_users_edit_submit',        '/admin/users/edit/submit')
    config.add_route('admin_users_email',              '/admin/users/email')
    config.add_route('admin_users_email_deadbeats',    '/admin/users/email/deadbeats')
    config.add_route('admin_users_email_all',          '/admin/users/email/all')
    config.add_route('admin_user',                     '/admin/user/{user_id}')
    config.add_route('admin_user_balance_edit',        '/admin/user/balance/edit')
    config.add_route('admin_user_balance_edit_submit', '/admin/user/balance/edit/submit')
    config.add_route('admin_user_password_create',     '/admin/user/{user_id}/password/create')
    config.add_route('admin_user_password_reset',      '/admin/user/{user_id}/password/reset')

    config.add_route('admin_pools',                    '/admin/pools')
    config.add_route('admin_pool',                     '/admin/pool/{pool_id}')
    config.add_route('admin_pool_addmember_submit',    '/admin/pool/addmember/submit')

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

    config.add_route('admin_restocks',       '/admin/restocks')
    config.add_route('admin_events',         '/admin/events')
    config.add_route('admin_events_load_more','/admin/events/load_more')
    config.add_route('admin_events_deleted', '/admin/events/deleted')
    config.add_route('admin_event_upload',   '/admin/event/upload')
    config.add_route('admin_event',          '/admin/event/{event_id}')
    config.add_route('admin_event_undo',     '/admin/event/undo/{event_id}')
    config.add_route('admin_event_receipt',  '/admin/event/receipt/{receipt_id}.pdf')

    config.add_route('admin_password_edit',        '/admin/password/edit')
    config.add_route('admin_password_edit_submit', '/admin/password/edit/submit')

    config.add_route('admin_shopping_list',   '/admin/shopping')

    config.add_route('admin_requests',        '/admin/requests')

    config.add_route('admin_announcements_edit',        '/admin/announcements/edit')
    config.add_route('admin_announcements_edit_submit', '/admin/announcements/edit/submit')
    config.add_route('admin_tweet_submit',              '/admin/tweet/submit')



    config.add_route('admin_data_items_json',    '/admin/data/items/{period}')
    config.add_route('admin_data_sales_json',    '/admin/data/sales/{period}')
    config.add_route('admin_data_deposits_json', '/admin/data/deposits/{period}')

    config.add_route('admin_data_items_each_json', '/admin/data/items/{period}/each')
    config.add_route('admin_data_sales_each_json', '/admin/data/sales/{period}/each')
    config.add_route('admin_data_deposits_each_json', '/admin/data/deposits/{period}/each')

    config.add_route('admin_data_item_sales_json', '/admin/data/item/sales/{item_id}')

    config.add_route('admin_data_users_totals_json', '/admin/data/users/totals')

    config.add_route('admin_data_speed_items', '/admin/data/speed/items')

    # DYNAMIC CONTENT
    config.add_route('dynamic_item_img', '/dynamic/item/{item_id}.jpg')


    config.add_route('login',  '/login')
    config.add_route('logout', '/logout')
    config.add_request_method(get_user, "user", reify=True)

    # 404 Page
    config.add_view(notfound, context='pyramid.httpexceptions.HTTPNotFound')

    config.scan(".views")
    config.scan(".views_user")
    config.scan(".views_admin")
    config.scan(".views_data")
    config.scan(".views_dynamic")

    return config.make_wsgi_app()
