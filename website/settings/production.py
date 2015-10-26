import os
from .base import *


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']
SECRET_KNUTH_PRIME = int(os.environ['SECRET_KNUTH_PRIME'])
SECRET_KNUTH_INVERSE = int(os.environ['SECRET_KNUTH_INVERSE'])
SECRET_KNUTH_RANDOM = int(os.environ['SECRET_KNUTH_RANDOM'])

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['ten-minute-secret.herokuapp.com', ]

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

import dj_database_url
DATABASES = {}
DATABASES['default'] =  dj_database_url.config()

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 15552000
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
