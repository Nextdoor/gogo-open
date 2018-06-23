from functools import wraps
import httplib2

import flask
from flask.views import MethodView
from apiclient import discovery
from oauth2client import client

flow = None


def init_app(app):
    global flow
    flow = client.flow_from_clientsecrets(
        '/app/resources/client_secrets.json',
        scope=['https://www.googleapis.com/auth/userinfo.email'],
        redirect_uri=app.config['REDIRECT_URI'])
    flow.user_agent = 'Go Link Shortener'


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if current_user is None:
            flask.session['after_auth'] = flask.request.url
            return flask.redirect(flow.step1_get_authorize_url())
        if 'after_auth' in flask.session:
            return flask.redirect(flask.session.pop('after_auth'))
        return f(*args, **kwargs)

    return decorated_function


class OAuth2Callback(MethodView):
    def get(self):
        code = flask.request.args.get('code')
        if code is None:
            return flask.redirect(flow.step1_get_authorize_url())
        credentials = flow.step2_exchange(code)
        try:
            flask.session['user'] = query_user(credentials, flask.current_app.config['HOSTED_DOMAIN'])
        except ValueError:
            flask.session.pop('after_auth')
            return 'Unauthorized', 401
        return flask.redirect('/')


def query_user(credentials, hosted_domain):
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('oauth2', 'v2', http=http)
    result = service.userinfo().get().execute()
    email = result['email']
    if f'@{hosted_domain}' not in email:
        raise ValueError(f'Must be a {hosted_domain} domain.')
    return email.split(f'@{hosted_domain}')[0]


def get_current_user():
    return flask.session.get('user')
