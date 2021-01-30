"""
Django settings for restaurant project.

Generated by 'django-admin startproject' using Django 3.1.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import os
from pathlib import Path
from datetime import time
# set ExtendedLogger as default logger
from common.logging.logger import ExtendedLogger


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    #### 'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # configure each application by subclassing AppConfig in apps.py of
    # each application folder, give dotted path of the subclass at here
    # to complete application registry.
    'rest_framework',
    'softdelete.apps.SoftdeleteConfig',
    'location.apps.LocationConfig',
    'user_management.apps.UserManagementConfig',
]

# Note:
# this project is staff-only backend site for PoS system, concurrent login
# on individual account is prohibited.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'common.auth.middleware.ExtendedCsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'common.sessions.middleware.OneSessionPerAccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'user_management.root_urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['my_templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

FIXTURE_DIRS = ['my_fixtures',]

WSGI_APPLICATION = 'restaurant.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = { # will be update with secrets at the bottom of file
    'default': { # only give minimal privilege to start django app server
        'ENGINE': 'django.db.backends.mysql',
        'CONN_MAX_AGE': 0, # set 0 only for debugging purpose
    },
    'site_dba': { # apply this setup only when you run management commands at backend server
        'ENGINE': 'django.db.backends.mysql',
        'CONN_MAX_AGE': 0,
    },
    'usermgt_service': {
        'ENGINE': 'django.db.backends.mysql',
        'CONN_MAX_AGE': 0,
        'reversed_app_label': ['user_management', 'auth', 'location']
    },
} # end of database settings

DATABASE_ROUTERS = ['common.models.db.ServiceModelRouter']


# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


AUTHENTICATION_BACKENDS = ['common.auth.backends.ExtendedModelBackend']

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# expire time may vary based on user groups or roles,
# will need to configure this programmatically
SESSION_COOKIE_AGE = 600

### SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_ENGINE = 'common.sessions.backends.file'

SESSION_SERIALIZER = 'common.sessions.serializers.ExtendedJSONSerializer'

SESSION_FILE_PATH = os.path.join(BASE_DIR ,'tmp/sessions')

# the name of request header used for CSRF authentication,
# e.g. according to setting below, frontend may send request "anti-csrf-tok" in the header
CSRF_HEADER_NAME = 'HTTP_X_ANTI_CSRF_TOK'

CSRF_COOKIE_NAME = 'anticsrftok'

# the CSRF token is stored at client side (browser cookie) and should expire as soon as
# the session expires (for logged-in users) , or each valid token should last 12 hours for
# unauthentication accesses.
CSRF_COOKIE_AGE  = 12 * 3600 ## 43


CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.path.join(BASE_DIR ,'tmp/cache/django/default'),
            'TIMEOUT': 3600,
            'OPTIONS': {
                'MAX_ENTRIES': 512,
                # TODO, figure out how to use KEY_PREFIX and KEY_FUNCTION
                },
            },
        'user_session': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.path.join(BASE_DIR ,'tmp/cache/django/user_session'),
            'TIMEOUT': 86400,
            'OPTIONS': {
                'MAX_ENTRIES': 512,
                },
            },
        'log_level_change': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.path.join(BASE_DIR ,'tmp/cache/django/log_level_change'),
            'TIMEOUT': None,
            'OPTIONS': {
                'MAX_ENTRIES': 1024,
                },
            },
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Taipei'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
##### print("BASE_DIR.parent : "+ str(BASE_DIR.parent))

STATIC_ROOT = str(BASE_DIR.parent) + "/static"

# it means the URL http://your_domain_name/static/
STATIC_URL = '/static/'

# besides static files for specific application, there are static files that
# are commonly applied to multiple applications of a project. Here are paths
# to the common static files
COMMON_STATIC_PATH = os.path.join(BASE_DIR ,'common/static')
STATICFILES_DIRS = [str(COMMON_STATIC_PATH),]

DATA_UPLOAD_MAX_NUMBER_FIELDS = 400


# use bcrypt + SHA256 as default password hashing function.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]

# logging
_LOG_BASE_DIR = os.path.join(BASE_DIR ,'tmp/log/staffsite')
_LOG_FMT_DBG_BASE = ["{asctime}", "{levelname}", "{process:d}", "{thread:d}", "{pathname}", "{lineno:d}", "{message}"]
_LOG_FMT_DBG_VIEW = ["{req_ip}", "{req_mthd}", "{uri}"] + _LOG_FMT_DBG_BASE


LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'shortened_fmt': {
                'format': "%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s",
            },
            'dbg_base_fmt': {
                'format': ' '.join(_LOG_FMT_DBG_BASE),
                'style': '{',
            },
            'dbg_view_fmt': {
                'format': ' '.join(_LOG_FMT_DBG_VIEW),
                'style': '{',
            },
        },
        # pre-defined handler classes applied to this project
        'handlers': {
            #'console': {
            #    'level': 'ERROR',
            #    'formatter': 'shortened_fmt',
            #    'class': 'logging.StreamHandler',
            #    'stream': 'ext://sys.stdout',
            #},
            "default_file": {
                'level': 'WARNING',
                'formatter': 'shortened_fmt',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': str(os.path.join(_LOG_BASE_DIR, 'default.log')),
                # daily log, keep all log files for one year
                'backupCount': 366,
                # new file is created every 0 am (local time)
                'atTime': time(hour=0, minute=0, second=0),
                'encoding': 'utf-8',
                'delay': True, # lazy creation
            },
            "dbg_views_file": {
                'level': 'INFO',
                'formatter': 'dbg_view_fmt',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': str(os.path.join(_LOG_BASE_DIR, 'views.log')),
                'backupCount': 150,
                'atTime': time(hour=0, minute=0, second=0),
                'encoding': 'utf-8',
                'delay': True, # lazy creation
            },
            "dbg_views_logstash": {
                'level': 'DEBUG',
                'formatter': 'dbg_view_fmt',
                'class':    'logstash_async.handler.AsynchronousLogstashHandler',
                'transport':'logstash_async.transport.TcpTransport',
                'host': 'localhost',
                'port': 5959,
                'database_path': None,
                # In this project logstash input server and django server are hosted in the
                # same machine, therefore it's not necessary to enable secure connection.
                'ssl_enable': False,
            },
            "dbg_base_logstash": {
                'level': 'DEBUG',
                'formatter': 'dbg_base_fmt',
                'class':    'logstash_async.handler.AsynchronousLogstashHandler',
                'transport':'logstash_async.transport.TcpTransport',
                'host': 'localhost',
                'port': 5959,
                'database_path': None,
                'ssl_enable': False,
            },
        }, # end of handlers section
        'loggers': {
            'common.views': {
                'level': 'INFO',
                'handlers': ['dbg_views_file', 'dbg_views_logstash'],
            },
            'common.views.mixins': {
                'level': 'INFO',
                'handlers': ['dbg_views_file', 'dbg_views_logstash'],
            },
            'common.views.filters': {
                'level': 'WARNING',
                'handlers': ['dbg_views_logstash'],
            },
            'common.serializers': {
                'level': 'INFO',
                'handlers': ['dbg_base_logstash'],
            },
            'common.serializers.mixins.nested': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'common.serializers.mixins.quota': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'common.serializers.mixins.closure_table': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'common.validators': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'common.models.closure_table': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'common.models.db': {
                'level': 'INFO',
                'handlers': ['dbg_base_logstash'],
            },
            'common.models.migrations': {
                'level': 'INFO',
                'handlers': ['default_file', 'dbg_base_logstash'],
            },
            'common.auth.backends': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'common.sessions.middleware': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'common.sessions.serializers': {
                'level': 'ERROR',
                'handlers': ['dbg_base_logstash'],
            },
            'common.util.python.elasticsearch': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'common.util.python.async_tasks': {
                'level': 'INFO',
                'handlers': ['dbg_base_logstash'],
            },
            'user_management.views.html': {
                'level': 'INFO',
                'handlers': ['dbg_views_file', 'dbg_views_logstash'],
            },
            'user_management.views.api': {
                'level': 'INFO',
                'handlers': ['dbg_views_file', 'dbg_views_logstash'],
            },
            'user_management.views.common': {
                'level': 'WARNING',
                'handlers': ['dbg_views_logstash'],
            },
            'user_management.serializers.nested': {
                'level': 'INFO',
                'handlers': ['dbg_base_logstash'],
            },
            'user_management.serializers': {
                'level': 'INFO',
                'handlers': ['dbg_base_logstash'],
            },
            'user_management.models': {
                'level': 'INFO',
                'handlers': ['dbg_base_logstash'],
            },
            'user_management.permissions': {
                'level': 'WARNING',
                'handlers': ['dbg_views_logstash'],
            },
            'user_management.async_tasks': {
                'level': 'INFO',
                'handlers': ['dbg_base_logstash'],
            },
            'user_management.queryset': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'softdelete.models': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'softdelete.views': {
                'level': 'INFO',
                'handlers': ['dbg_views_logstash'],
            },
        }, # end of loggers section
        'root': {
            'level': 'ERROR',
            'handlers': ['default_file'],
        },
} # end of LOGGING


REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    #'PAGE_SIZE' : 40
}



# mailing function setup
DEFAULT_FROM_EMAIL = 'system@yourproject.io'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True



from common.util.python.django.setup  import setup_secrets

setup_secrets(secrets_path='./common/data/secrets.json', module_path=__name__)

