"""
Django 5.2.1. settings for SonicAdz.

"""

from pathlib import Path
from cloudinary import config
from django.urls import reverse_lazy
import os 
import dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


dotenv.load_dotenv()


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", '')


DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")


AUTH_USER_MODEL = "users.User"


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Local apps
    'users',
    'core',
    'creators',
    'advertisers',
    'miniapp',
    'payments',
    'api',
    
    # 3rd app
    "allauth",
    "allauth.account",
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    'core.middleware.user_type_access_middleware.UserTypeAccessMiddleware', 
    'core.middleware.channel_verification_middleware.ChannelVerificationMiddleware',
    'core.middleware.payment_verification.CreatorPaymentVerificationMiddleware',
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database

if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.parse(os.getenv('RENDER_DATABASE_URL')),
        'supabase': dj_database_url.parse(os.getenv('BACKUP_DATABASE_URL')),
    }

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = 'Africa/Addis_Ababa'  #"UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


if DEBUG:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
else:
    DEFAULT_FILE_STORAGE = 'storages.backends.cloudinary.CloudinaryStorage'
    
    
# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 30,
}



EMAIL_BACKEND = 'core.email_backend.BrevoEmailBackend'

SENDINBLUE_API_KEY = os.getenv("SENDINBLUE_API_KEY", "")  
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@sonicadz.com")  
FROM_NAME = os.getenv('FROM_NAME', 'CEO')


# Authentication Configuration & Session Management Settings
PHONENUMBER_DEFAULT_REGION = 'ET'

LOGIN_REDIRECT_URL = reverse_lazy('advertiser:dashboard')
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'

ACCOUNT_SESSION_REMEMBER = None

# Email & Signup Behavior
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_SUBJECT_PREFIX = 'SonicAdz. '
ACCOUNT_EMAIL_PLAIN = False
# Security & Rate Limiting
ACCOUNT_PREVENT_ENUMERATION = 'strict'
ACCOUNT_RATE_LIMITS = {
    'login': '5/m',
    'signup': '5/m',
}
ACCOUNT_REAUTHENTICATION_TIMEOUT = 3600

# Forms & Customization
ACCOUNT_SIGNUP_FIELDS = ['phone_number*', 'email*', 'password1*', 'password2*']
ACCOUNT_SIGNUP_FORM_CLASS = 'users.forms.UsersSignupForm'
# ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = 'phone_number'
ACCOUNT_USERNAME_BLACKLIST = ['admin', 'root']
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_MAX_EMAIL_ADDRESSES = 1
ACCOUNT_EMAIL_NOTIFICATIONS = False


ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = LOGIN_REDIRECT_URL # or None
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = '/accounts/login/' # or to /welcome/


# Setting Variables 
SUPERUSER_PASSWORD = os.getenv('SUPERUSER_PASSWORD')
BOT_LINK = os.getenv('BOT_LINK', '')
BOT_ID = os.getenv('BOT_ID', '')
BOT_SECRET_TOKEN = os.getenv('BOT_SECRET_TOKEN', '')
ADMIN_USER = os.getenv('ADMIN_USER', '123456789')
PORT_ARCH_ID = os.getenv('PORT_ARCH_ID', '')
MINIAPP = os.getenv('MINIAPP', 'miniapp')
INTERNAL_VERIFY_API_URL = os.getenv('INTERNAL_VERIFY_API_URL')
TELEGRAM_SECRET_TOKEN = os.getenv('TELEGRAM_SECRET_TOKEN', '')
PLATFORM_FEE = os.getenv('PLATFORM_FEE', 15)
CHAPA_SECRET_KEY = os.getenv('CHAPA_SECRET_KEY', 'csecret')



cloudinary_config = {
    'cloud_name': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'api_key': os.getenv('CLOUDINARY_API_KEY'),
    'api_secret': os.getenv('CLOUDINARY_API_SECRET'),
    
}

config(**cloudinary_config, secure=True)




LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },

    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },

    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'payments': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}
