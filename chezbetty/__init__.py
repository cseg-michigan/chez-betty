from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.httpexceptions import HTTPFound
import pyramid.httpexceptions
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
from .models import reimbursee
from .models import badscan
from .models.model import *
from .models.user import LDAPLookup, groupfinder, get_user, User
from .btc import Bitcoin

###
### 404
###
def notfound(request):
    ## 404 Logic:
    # If there is a "." in the request path, then we assume this is not a user
    # facing page but instead a javascript file or other helper file.
    # If we cannot find that file, we want to actually 404.
    # If the path looks like "/terminal/users" and we can't find that, then we
    # want to redirect to a known page so the terminal keeps working.
    if '.' in request.path:
        return pyramid.httpexceptions.HTTPNotFound(body_template='<a href="/">Home</a>')
    else:
        request.session.flash('404: Could not find that page. Redirected to home.', 'error')
        return HTTPFound(location=request.route_url('index'))

###
### main()
###
### Setup all routes and other config settings
###
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

    config.add_renderer('csv', 'chezbetty.renderers.CSVRenderer')

    # GLOBAL NOT LOGGED IN VIEWS
    config.add_route('exception_view',      '/exception')

    config.add_route('index',                    '/')
    config.add_route('lang',                     '/lang-{code}')
    config.add_route('about',                    '/about')
    config.add_route('items',                    '/items')

    config.add_route('paydebt',                  '/paydebt/{uniqname}')
    config.add_route('paydebt_submit',           '/paydebt/{uniqname}/submit')


    # TERMINAL VIEWS
    config.add_route('terminal_force_index',     '/force_terminal')

    config.add_route('terminal_umid_check',      '/terminal/check')

    config.add_route('terminal_deposit',         '/terminal/deposit')
    # config.add_route('terminal_deposit_delete',  '/terminal/deposit/delete')

    config.add_route('terminal_item_id',         '/terminal/item/id/{item_id}')
    config.add_route('terminal_item_barcode',    '/terminal/item/barcode/{barcode}')

    config.add_route('terminal_purchase',        '/terminal/purchase')
    config.add_route('terminal_purchase_delete', '/terminal/purchase/delete')
    config.add_route('terminal_purchase_tag',    '/terminal/purchase/tag/{tag_id}')

    config.add_route('terminal',                 '/terminal/{umid}')


    # USER ADMIN
    config.add_route('user_index',                 '/user')
    # Map this as convenience since users will be typing manually often
    config.add_route('user_index_slash',           '/user/')

    config.add_route('user_ajax_bool',             '/user/ajax/bool/{object}/{id}/{field}/{state}')

    config.add_route('user_deposit_cc',            '/user/deposit_cc')
    config.add_route('user_deposit_cc_custom',     '/user/deposit_cc/custom')
    config.add_route('user_deposit_cc_submit',     '/user/deposit_cc/submit')

    config.add_route('user_item_list',             '/user/item/list')

    config.add_route('user_ajax_item_request_fuzzy','/user/ajax/item/request/new/fuzzy')
    config.add_route('user_item_request',          '/user/item/request')
    config.add_route('user_item_request_new',      '/user/item/request/new')
    config.add_route('user_item_request_post_new', '/user/item/request/{id}/post/new')

    config.add_route('user_pools',                 '/user/pools')
    config.add_route('user_pools_new_submit',      '/user/pools/new/submit')
    config.add_route('user_pool',                  '/user/pool/{pool_id}')
    config.add_route('user_pool_addmember_submit', '/user/pool/addmember/submit')
    config.add_route('user_pool_changename_submit','/user/pool/changename/submit')

    config.add_route('user_password_edit',         '/user/password/edit')
    config.add_route('user_password_edit_submit',  '/user/password/edit/submit')


    # ADMIN
    config.add_route('admin_index',             '/admin')
    config.add_route('admin_index_dashboard',   '/admin/dashboard')
    config.add_route('admin_index_history',     '/admin/history')
    config.add_route('admin_index_history_year','/admin/history/year/{year}')
    config.add_route('admin_index_history_month','/admin/history/month/{month}')
    config.add_route('admin_index_history_academic','/admin/history/academic/{year}')
    config.add_route('admin_index_history_semesters','/admin/history/semester/{semester}')

    config.add_route('admin_ajax_bool',         '/admin/ajax/bool/{object}/{id}/{field}/{value}')
    config.add_route('admin_ajax_text',         '/admin/ajax/text/{object}/{id}/{field}')
    config.add_route('admin_ajax_new',          '/admin/ajax/new/{object}/{arg}')
    config.add_route('admin_ajax_delete',       '/admin/ajax/delete/{object}/{id}')
    config.add_route('admin_ajax_connection',   '/admin/ajax/connection/{object1}/{object2}/{arg1}/{arg2}')

    config.add_route('admin_ajaxed_field',      '/admin/ajax/field/{field}')

    config.add_route('admin_item_barcode_json', '/admin/item/barcode/{barcode}/json')
    config.add_route('admin_item_id_json',      '/admin/item/id/{id}/json')
    config.add_route('admin_item_search_json',  '/admin/item/search/{search}/json')
    config.add_route('admin_restock',           '/admin/restock')
    config.add_route('admin_restock_submit',    '/admin/restock/submit')

    config.add_route('admin_items_add',         '/admin/items/add')
    config.add_route('admin_items_add_submit',  '/admin/items/add/submit')
    config.add_route('admin_items_list',        '/admin/items/list')
    config.add_route('admin_item_edit_submit',  '/admin/item/edit/submit')
    config.add_route('admin_item_edit',         '/admin/item/edit/{item_id}')
    config.add_route('admin_item_barcode_pdf',  '/admin/item/barcode/{item_id}.pdf')
    config.add_route('admin_item_delete',       '/admin/item/delete/{item_id}')
    config.add_route('admin_badscans_list',     '/admin/badscans/list')

    config.add_route('admin_tags_list',         '/admin/tags/list')

    config.add_route('admin_box_add',           '/admin/box/add')
    config.add_route('admin_box_add_submit',    '/admin/box/add/submit')
    config.add_route('admin_boxes_list',        '/admin/boxes/list')
    config.add_route('admin_box_edit_submit',   '/admin/box/edit/submit')
    config.add_route('admin_box_edit',          '/admin/box/edit/{box_id}')
    config.add_route('admin_box_delete',        '/admin/box/delete/{box_id}')

    config.add_route('admin_vendors_list',              '/admin/vendors/list')
    config.add_route('admin_vendors_add_submit',        '/admin/vendors/add/submit')
    config.add_route('admin_vendor_edit_submit',        '/admin/vendor/edit/submit')
    config.add_route('admin_vendor_edit',               '/admin/vendor/edit/{vendor_id}')

    config.add_route('admin_reimbursees',               '/admin/reimbursees')
    config.add_route('admin_reimbursees_add_submit',    '/admin/reimbursees/add/submit')
    config.add_route('admin_reimbursees_reimbursement_submit',    '/admin/reimbursees/reimbursement/submit')

    config.add_route('admin_inventory',                 '/admin/inventory')
    config.add_route('admin_inventory_submit',          '/admin/inventory/submit')

    config.add_route('admin_users_list',                '/admin/users/list')
    config.add_route('admin_users_archive_old_submit',  '/admin/users/archive/old/submit')
    config.add_route('admin_users_stats',               '/admin/users/stats')
    config.add_route('admin_users_email',               '/admin/users/email')
    config.add_route('admin_users_email_endofsemester', '/admin/users/email/endofsemester')
    config.add_route('admin_users_email_debt',          '/admin/users/email/debt/{type}')
    config.add_route('admin_users_email_oneperson',     '/admin/users/email/oneperson')
    config.add_route('admin_users_email_purchasers',    '/admin/users/email/purchasers')
    config.add_route('admin_users_email_all',           '/admin/users/email/all')
    config.add_route('admin_users_email_alumni',        '/admin/users/email/alumni')
    config.add_route('admin_user',                      '/admin/user/{user_id}')
    config.add_route('admin_uniqname',                  '/admin/uniqname/{uniqname}')
    config.add_route('admin_user_details',              '/admin/user/{user_id}/details')
    config.add_route('admin_user_search_json',          '/admin/user/search/{search}/json')
    config.add_route('admin_user_balance_edit',         '/admin/user/balance/edit')
    config.add_route('admin_user_balance_edit_submit',  '/admin/user/balance/edit/submit')
    config.add_route('admin_user_purchase_add',         '/admin/user/purchase/add')
    config.add_route('admin_user_purchase_add_submit',  '/admin/user/purchase/add/submit')
    config.add_route('admin_user_password_create',      '/admin/user/{user_id}/password/create')
    config.add_route('admin_user_password_reset',       '/admin/user/{user_id}/password/reset')
    config.add_route('admin_user_archive',              '/admin/user/{user_id}/archive')
    config.add_route('admin_user_changename',           '/admin/user/{user_id}/changename/{name}')
    config.add_route('admin_user_changerole',           '/admin/user/{user_id}/changerole/{role}')

    config.add_route('admin_pools',                     '/admin/pools')
    config.add_route('admin_pool',                      '/admin/pool/{pool_id}')
    config.add_route('admin_pool_name',                 '/admin/pool/{pool_id}/name')
    config.add_route('admin_pool_addmember_submit',     '/admin/pool/addmember/submit')

    config.add_route('admin_cash_reconcile',            '/admin/cash/reconcile')
    config.add_route('admin_cash_reconcile_submit',     '/admin/cash/reconcile/submit')

    config.add_route('admin_cash_adjustment',           '/admin/cash/adjustment')
    config.add_route('admin_cash_donation_submit',      '/admin/cash/donation/submit')
    config.add_route('admin_cash_withdrawal_submit',    '/admin/cash/withdrawal/submit')
    config.add_route('admin_cash_adjustment_submit',    '/admin/cash/adjustment/submit')

    config.add_route('admin_btc_reconcile',             '/admin/btc/reconcile')
    config.add_route('admin_btc_reconcile_submit',      '/admin/btc/reconcile/submit')

    config.add_route('admin_events',                    '/admin/events')
    config.add_route('admin_events_load_more',          '/admin/events/load_more')
    config.add_route('admin_event_upload',              '/admin/event/upload')
    config.add_route('admin_event',                     '/admin/event/{event_id}')
    config.add_route('admin_event_undo',                '/admin/event/undo/{event_id}')
    config.add_route('admin_event_receipt',             '/admin/event/receipt/{receipt_id}.pdf')

    config.add_route('admin_password_edit',             '/admin/password/edit')
    config.add_route('admin_password_edit_submit',      '/admin/password/edit/submit')

    config.add_route('admin_requests',                  '/admin/requests')
    config.add_route('admin_item_request_post_new',     '/admin/item/request/{id}/post/new')

    config.add_route('admin_announcements_edit',        '/admin/announcements/edit')
    config.add_route('admin_announcements_edit_submit', '/admin/announcements/edit/submit')
    config.add_route('admin_tweet_submit',              '/admin/tweet/submit')



    config.add_route('admin_data_items_json',           '/admin/data/items/{period}')
    config.add_route('admin_data_sales_json',           '/admin/data/sales/{period}')
    config.add_route('admin_data_deposits_json',        '/admin/data/deposits/{period}')

    config.add_route('admin_data_json_highcharts',      '/admin/data/raw/{metric}/{period}')

    config.add_route('admin_data_items_each_json',      '/admin/data/items/{period}/each')
    config.add_route('admin_data_sales_each_json',      '/admin/data/sales/{period}/each')
    config.add_route('admin_data_deposits_each_json',   '/admin/data/deposits/{period}/each')

    config.add_route('admin_data_item_sales_json',      '/admin/data/item/sales/{item_id}')

    config.add_route('admin_data_users_totals_json',                   '/admin/data/users/totals')
    config.add_route('admin_data_users_balance_totals_json',           '/admin/data/users/balance/totals')
    # config.add_route('admin_data_users_balance_totals_percapita_json', '/admin/data/users/balance/totalspc')

    config.add_route('admin_data_user_balance_json',    '/admin/data/user/{user_id}/balances')

    config.add_route('admin_data_speed_items',          '/admin/data/speed/items')

    config.add_route('admin_data_histogram_balances',   '/admin/data/histogram/balances')
    config.add_route('admin_data_histogram_dayssincepurchase',   '/admin/data/histogram/dayssincepurchase')
    config.add_route('admin_data_histogram_numberofpurchases',   '/admin/data/histogram/numberofpurchases')

    # DYNAMIC CONTENT
    config.add_route('dynamic_item_img', '/dynamic/item/{item_id}.jpg')


    config.add_route('login',          '/login')
    config.add_route('login_submit',   '/login/submit')
    config.add_route('login_reset_pw', '/login/reset_pw')
    config.add_route('logout',         '/logout')
    config.add_request_method(get_user, "user", reify=True)

    # 404 Page
    config.add_view(notfound, context='pyramid.httpexceptions.HTTPNotFound')

    config.scan(".views")
    config.scan(".views_public")
    config.scan(".views_terminal")
    config.scan(".views_user")
    config.scan(".views_admin")
    config.scan(".views_data")
    config.scan(".views_dynamic")

    return config.make_wsgi_app()
