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
from ecommerce_common.logging.logger import ExtendedLogger
from ecommerce_common.util.django.setup  import setup_secrets


BASE_DIR = Path(os.environ['SERVICE_BASE_PATH']).resolve(strict=True)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = []

# Note:
# this project is staff-only backend site for PoS system, concurrent login
# on individual account is prohibited.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

# no URL is allowed
ROOT_URLCONF = None

TEMPLATES = [
    { # will be used when rendering email content
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    }
]

FIXTURE_DIRS = []

WSGI_APPLICATION = 'restaurant.wsgi.application'

# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {}
DATABASE_ROUTERS = []

# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []

AUTHENTICATION_BACKENDS = []

# the name of request header used for CSRF authentication,
# e.g. according to setting below, frontend may send request "anti-csrf-tok" in the header


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


DATA_UPLOAD_MAX_NUMBER_FIELDS = 400


# use bcrypt + SHA256 as default password hashing function.
PASSWORD_HASHERS = []

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
            'ecommerce_common.util.elasticsearch': {
                'level': 'WARNING',
                'handlers': ['dbg_base_logstash'],
            },
            'ecommerce_common.util.async_tasks': {
                'level': 'INFO',
                'handlers': ["dbg_base_logstash", "default_file"],
            },
            'ecommerce_common.util.periodic_tasks': {
                'level': 'INFO',
                'handlers': ['dbg_base_logstash'],
            },
        }, # end of loggers section
        'root': {
            'level': 'ERROR',
            'handlers': ['default_file'],
        },
} # end of LOGGING


# mailing function setup
DEFAULT_FROM_EMAIL = 'system@yourproject.io'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True

setup_secrets(
    secrets_path = os.path.join(BASE_DIR, 'common/data/secrets.json'),
    module_path=__name__, portal_type='staff', interface_type='internal'
)
