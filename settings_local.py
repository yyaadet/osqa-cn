# encoding:utf-8
import os.path

SITE_SRC_ROOT = os.path.dirname(__file__)
LOG_FILENAME = 'debug.osqa.log'

#for logging
import logging
logging.basicConfig(
    filename=os.path.join(SITE_SRC_ROOT, 'log', LOG_FILENAME),
    level=logging.ERROR,
    format='%(pathname)s TIME: %(asctime)s MSG: %(filename)s:%(funcName)s:%(lineno)d %(message)s',
)

#ADMINS and MANAGERS
ADMINS = ()
MANAGERS = ADMINS

DEBUG = True
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': True
}
TEMPLATE_DEBUG = DEBUG
INTERNAL_IPS = ('127.0.0.1',)


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "osqa",
        "USER": "",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
        "PORT": "3306",
    },
}


CACHE_BACKEND = 'file://%s' % os.path.join(os.path.dirname(__file__),'cache').replace('\\','/')
SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# This should be equal to your domain name, plus the web application context.
# This shouldn't be followed by a trailing slash.
# I.e., http://www.yoursite.com or http://www.hostedsite.com/yourhostapp
APP_URL = 'http://www.17yob.com'

#LOCALIZATIONS
TIME_ZONE = 'Asia/Shanghai'

#OTHER SETTINGS

USE_I18N = True
LANGUAGE_CODE = 'zh.CN'

DJANGO_VERSION = 1.3
OSQA_DEFAULT_SKIN = 'default'

DISABLED_MODULES = ['books', 'project_badges', 'facebookauth', 'recaptcha']

#refer to djangosphinx documentation
SPHINX_API_VERSION = 0x116
SPHINX_SEARCH_INDICES=('osqa_question_index',) #a tuple of index names remember about a comma after the#last item, especially if you have just one :)
SPHINX_SERVER='localhost'
SPHINX_PORT=9312

