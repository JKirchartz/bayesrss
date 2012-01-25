import os, sys, glob 
import unittest 
import doctest 
from os.path import dirname, basename, splitext, join 
TESTDIR = dirname(__file__) 
MAINDIR = dirname(TESTDIR) 
GOOGLE_PATH = "/usr/local/google_appengine" 
EXTRA_PATHS = [ 
    TESTDIR, 
    MAINDIR, 
    GOOGLE_PATH, 
    os.path.join(GOOGLE_PATH, 'lib', 'django_1_2'), 
    os.path.join(GOOGLE_PATH, 'lib', 'webob'), 
    os.path.join(GOOGLE_PATH, 'lib', 'yaml', 'lib'), 
] 
for directory in EXTRA_PATHS: 
    if not directory in sys.path: 
        sys.path.insert(0, directory) 

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api import mail_stub
from google.appengine.api import urlfetch_stub
from google.appengine.api import user_service_stub

APP_ID = u'test_app'
AUTH_DOMAIN = 'gmail.com'
LOGGED_IN_USER = ''  # set to '' for no logged in user

# Start with a fresh api proxy.
apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()

# Use a fresh stub datastore.
stub = datastore_file_stub.DatastoreFileStub(APP_ID, '/dev/null', '/dev/null')
apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)

# Use a fresh stub UserService.
apiproxy_stub_map.apiproxy.RegisterStub('user',
user_service_stub.UserServiceStub())
os.environ['AUTH_DOMAIN'] = AUTH_DOMAIN
os.environ['USER_EMAIL'] = LOGGED_IN_USER

# Use a fresh urlfetch stub.
apiproxy_stub_map.apiproxy.RegisterStub(
    'urlfetch', urlfetch_stub.URLFetchServiceStub())

# Use a fresh mail stub.
apiproxy_stub_map.apiproxy.RegisterStub(
  'mail', mail_stub.MailServiceStub())
