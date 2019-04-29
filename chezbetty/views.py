from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.security import Allow, Everyone, remember, forget
from pyramid.view import view_config, forbidden_view_config

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('betty')

from sqlalchemy.sql import func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import NoResultFound

from .models import *
from .models.model import *
from .models import user as __user
from .models.user import User
from .models.announcement import Announcement

from .utility import user_password_reset

import chezbetty.datalayer as datalayer
import transaction

import traceback

###
### Catch-all error page
###

@view_config(route_name='exception_view', renderer='templates/public/exception.jinja2')
def exception_view(request):
    return {}

@view_config(context=Exception)
def exception_view_handler(context, request):
    print('-'*80)
    print('An unknown error occurred:')
    print('\t** Some potentially useful information:')
    try:
        print('\t** request {}'.format(request))
        print('\t** client_addr {}'.format(request.client_addr))
        print('\t** authenticated_userid {}'.format(request.authenticated_userid))
        print('\t** GET {}'.format(request.GET))
        print('\t** POST {}'.format(request.POST))
        print('\t** url {}'.format(request.url))
        print('\t** user_agent {}'.format(request.user_agent))
        print('\t** headers.environ {}'.format(request.headers.environ))
        print('\t** referer {}'.format(request.referer))
        print('\t** body {}'.format(request.body))
    except:
        pass
    traceback.print_exc()
    print('-'*80)
    excepting_path = request.current_route_path()
    return HTTPFound(location=request.route_url('exception_view',
        _query={'excepting_path':excepting_path}))


###
### HTML Pages
###

### No login needed

@view_config(route_name='lang')
def lang(request):
    code = request.matchdict['code']
    response = Response()
    response.set_cookie('_LOCALE_', value=code, max_age=15*60) # reset lang after 15min

    return HTTPFound(location='/', headers=response.headers)


from pyramid.view import view_config

# Use to select which homepage to show, the only-on-the-betty-terminal version
# or the publically accessible version.
def IsTerminalPredicate(boolean):
    def is_terminal(context, request):
        return ((request.user != None) and (request.user.role == 'serviceaccount')) == boolean
    return is_terminal



def _index_terminal(request):
    announcements = Announcement.all_enabled()

    # For the demo mode
    admins = []
    if 'demo' in request.cookies and request.cookies['demo'] == '1':
        admins = User.get_admins()

    return {'announcements': announcements,
            'admins': admins,
            'owed_by_users': User.get_amount_owed()}


# Terminal home page
@view_config(route_name='index',
             renderer='templates/terminal/index.jinja2',
             custom_predicates=(IsTerminalPredicate(True),))
def index_terminal(request):
    return _index_terminal(request)


# Convenience route for checking in on things
@view_config(route_name='terminal_force_index',
             renderer='templates/terminal/index.jinja2')
def terminal_force_index(request):
    return _index_terminal(request)


# General internet homepage
@view_config(route_name='index',
             renderer='templates/public/index.jinja2',
             custom_predicates=(IsTerminalPredicate(False),))
def index(request):
    return {}

# Login routes
@view_config(route_name='login',
             renderer='templates/public/login.jinja2')
@forbidden_view_config(renderer='templates/public/login.jinja2')
def login(request):
    came_from = request.params.get('came_from', request.url)
    try:
        came_from = request.GET['redirect']
    except KeyError:
        pass

    return dict(
        login_message = '',
        url = '',
        came_from = came_from,
        login = '',
        password = ''
    )


@view_config(route_name='login_submit',
             renderer='templates/public/login.jinja2')
def login_submit(request):
    # Need to set this in case the password is wrong
    came_from = request.params.get('came_from', request.url)

    messages = []

    # See if this is a valid login attempt
    login    = request.params.get('login', '').lower()
    password = request.params.get('password', '')
    user     = DBSession.query(User).filter(User.uniqname == login).first()
    if user and not user.enabled:
        messages.append('Login failed. User not allowed to login.')
    elif user and user.check_password(password):
        # Got a successful login. Now decide where to direct the user.
        headers = remember(request, login)

        if user.role == 'serviceaccount':
            # This is the service account for using the terminal.
            # Go back to the home page
            return HTTPFound(location=request.route_url('index'), headers=headers)

        else:
            # On user login also check if the user is archived. A login
            # counts as activity
            if user.archived:
                if user.archived_balance != 0:
                    datalayer.adjust_user_balance(user,
                                                  user.archived_balance,
                                                  'Reinstated archived user.',
                                                  user)
                user.balance = user.archived_balance
                user.archived = False

            # If we got a normal user, check if the login form had
            # a "came_from" input which tells us where to go back to.
            # Otherwise, default to '/user'.
            came_from = request.params.get('came_from', '')

            # Fetch some strings to compare against
            login_url     = request.resource_url(request.context, 'login')
            login_sub_url = request.resource_url(request.context, 'login', 'submit')
            reset_pw_url  = request.resource_url(request.context, 'login', 'reset_pw')
            user_url      = request.resource_url(request.context, 'user')

            # Make sure we don't send the user back to useless pages
            if came_from in ['', login_url, login_sub_url, reset_pw_url]:
                came_from = user_url

        return HTTPFound(location=came_from, headers=headers)
    else:
        messages.append('Login failed. Incorrect username or password.')

    return dict(
        login_message = messages,
        url           = request.application_url + '/login',
        came_from     = came_from,
        login         = login,
        password      = password
    )


@view_config(route_name='login_reset_pw',
             request_method='POST',
             renderer='templates/public/login.jinja2')
def login_reset_pw(request):
    login_url = request.resource_url(request.context, 'login')
    login_reset_url = request.resource_url(request.context, 'login_reset_pw')
    referrer = request.url
    if referrer == login_url or referrer == login_reset_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)

    succ = '',
    err = '',

    # This will create a user automatically if they do not already exist
    try:
        with transaction.manager:
            user = User.from_umid(request.POST['umid'])
        user = DBSession.merge(user)

        if request.POST['uniqname'] != user.uniqname:
            raise __user.InvalidUserException()
    except:
        err = 'Bad uniqname or umid',
    else:
        user_password_reset(user)
        succ = ('Password set and emailed to {}@umich.edu.'.format(user.uniqname),)

    return dict(
        forgot_error = err,
        forgot_success = succ,
        url = request.application_url + '/login',
        came_from = came_from,
    )


@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = request.route_url('index'),
                     headers  = headers)

