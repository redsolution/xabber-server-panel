import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
PROJECT_ROOT = os.path.join(BASE_DIR, 'xabber_server_panel')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
STATIC_URL = '/static/'


FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440
FILE_UPLOAD_PERMISSIONS = 0o644  # права для записи файлов, размером > FILE_UPLOAD_MAX_MEMORY_SIZE
SECRET_KEY = 'django-insecure--$i1m4fmjutnxyoyuu(c&#!djlv^&47$n@55=snkwexoo%&9k%'

DEBUG = False

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'xabber_server_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'xabber_server_panel.installation.middleware.InstallationMiddleware',
    'xabber_server_panel.custom_auth.middleware.UnauthorizedMiddleware',
    'xabber_server_panel.base_modules.config.middleware.VirtualHostMiddleware'
]

ROOT_URLCONF = 'xabber_server_panel.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_ROOT, 'templates')],
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

WSGI_APPLICATION = 'xabber_server_panel.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.abspath(BASE_DIR), 'panel.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MODULES_DIR = os.path.join(BASE_DIR, 'modules')

# ======== Ejabberd settings ============= #

INSTALLATION_LOCK = os.path.join(PROJECT_ROOT, '.installation_lock')
EJD_DIR = os.path.join(BASE_DIR, "xmppserver")
EJABBERD_DUMP = os.path.join(PROJECT_ROOT, 'utils/psql/pg.sql')
EJABBERD_CONFIG_PATH = os.path.join(PROJECT_ROOT, 'xmppserver/etc/ejabberd/')
EJABBERD_MODULES_CONFIG_FILE = 'modules_config.yml'
EJABBERD_ADD_CONFIG_FILE = 'additional_config.yml'
EJABBERDCTL = os.path.join(PROJECT_ROOT, 'xmppserver/bin/ejabberdctl')

EJABBERD_STATE = os.path.join(PROJECT_ROOT, 'server_state')
EJABBERD_STATE_ON = 1
EJABBERD_STATE_OFF = 0
EJABBERD_DEFAULT_GROUP_NAME = "All"
EJABBERD_DEFAULT_GROUP_DESCRIPTION = "Contains all users on this virtual host"

PREDEFINED_CONFIG_FILE_PATH = "predefined_config.json"

EJABBERD_VHOSTS_CONFIG_FILE = 'virtual_hosts.yml'

EJABBERD_API_URL = 'http://127.0.0.1:5280/panel'
EJABBERD_API_TOKEN_TTL = 60 * 60 * 24 * 365
EJABBERD_API_SCOPES = 'sasl_auth'

MODULE_SERVER_FILES_DIR = ''
XMPP_CLIENT_PORT = '5222'
XMPP_SERVER_PORT = '5269'
XMPP_HTTP_PORT = '5443'
XMPP_HTTPS_PORT = '5280'
XMPPS_CLIENT_PORT = '5223'

USER_FILES = os.path.join(PROJECT_DIR, 'user_files')
MOD_NICK_AVATAR_FILES = os.path.join(PROJECT_DIR, 'rand_avatars')

PAGINATION_PAGE_SIZE = 30
HTTP_REQUEST_TIMEOUT = 5

# =========== AUTH ============ #
INSTALLED_APPS += ['xabber_server_panel.custom_auth']

LOGIN_REDIRECT_URL = '/auth/login/'
LOGIN_URL = '/auth/login/'

AUTHENTICATION_BACKENDS = [
    'xabber_server_panel.custom_auth.backends.CustomAuthBackend',
]

# =========== USERS =============== #
INSTALLED_APPS += ['xabber_server_panel.base_modules.users']

AUTH_USER_MODEL = 'users.User'

# ============ API ============#
INSTALLED_APPS += ['xabber_server_panel.api']

# ============ DASHBOARD ============#
INSTALLED_APPS += ['xabber_server_panel.base_modules.dashboard']

# ============ CIRCLES ===============#
INSTALLED_APPS += ['xabber_server_panel.base_modules.circles']

# ============ GROUPS ===============#
INSTALLED_APPS += ['xabber_server_panel.base_modules.groups']

# ============ REGISTRATION ===============#
INSTALLED_APPS += ['xabber_server_panel.base_modules.registration']

# ============ LOG ===============#
INSTALLED_APPS += ['xabber_server_panel.base_modules.log']
EJABBERD_LOG_DIR = os.path.join(EJD_DIR, 'var', 'log', 'ejabberd')
EJABBERD_LOG = os.path.join(EJABBERD_LOG_DIR, 'ejabberd.log')
DJANGO_LOG_DIR = os.path.join(BASE_DIR, 'logs')
DJANGO_LOG = os.path.join(DJANGO_LOG_DIR, 'django.log')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'rotate_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024 * 1024,  # 1 MB
            'backupCount': 10,  # Number of backup files to keep
            'formatter': 'verbose',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['rotate_file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
# Ensure the logs directory exists
os.makedirs(DJANGO_LOG_DIR, exist_ok=True)

# ============ CONFIG ===============#
INSTALLED_APPS += ['xabber_server_panel.base_modules.config']
DNS_SERVICE = 'https://dns.google/resolve'

# ============ INSTALLATION ===============#
INSTALLED_APPS += ['xabber_server_panel.installation']

# ============ DJANGO - CRONTAB ===============#
INSTALLED_APPS += ['xabber_server_panel.crontab']
CRON_JOB_TOKEN = ''

# ============ CERTIFICATES ===============#
INSTALLED_APPS += ['xabber_server_panel.certificates']
CERT_CONF_FILENAME = "acertmgr.conf"
CERT_DOMAIN_FILENAME = "domains.conf"
CERT_CONF_DIR = os.path.join(PROJECT_DIR, 'acertmgr')
CERTS_DIR = os.path.join(PROJECT_DIR, 'certs')
CERT_VALIDATE_OCSP = "sha1" # mandated by RFC5019
CERT_API = "v2"
CERT_AUTHORITY = "https://acme-staging-v02.api.letsencrypt.org"
CHALLENGE_URL = "https://acme-challenge.xabber.com/challenge/"
CHALLENGE_RECORD = 'alias_acme-challenge.xabber.com.'
CERT_ACTION = None

# ============ WEBHOOKS ===============#
INSTALLED_APPS += ['xabber_server_panel.webhooks']
WEBHOOKS_SIGNATURE_HEADER = 'x-xmpp-server-signature'

# external modules
if os.path.exists(MODULES_DIR):
    for folder in os.listdir(MODULES_DIR):
        folder_path = os.path.join(MODULES_DIR, folder)
        if os.path.isdir(folder_path):
            app_name = "modules." + folder
            INSTALLED_APPS += [app_name]