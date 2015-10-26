from django.templatetags.static import static
from .base import *


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'bw&0^#v@gs=y^are5i3zd9*-sl382#_yafi^@o05$y(9$c=07v'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS += (
    'debug_toolbar',
)

DEBUG_TOOLBAR_CONFIG = dict(
    JQUERY_URL=static('admin/js/jquery.min.js'),
)

# CSP
CSP_DEFAULT_SRC += (
    # django exceptions
    "'unsafe-inline'",
    # debug toolbar
    "data:",
)

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, '..', 'db', 'development.sqlite3'),
    }
}

CSP_DEFAULT_SRC += (
    # django exceptions
    "'unsafe-inline'",
)
