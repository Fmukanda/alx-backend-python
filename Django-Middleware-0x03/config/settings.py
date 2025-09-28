# config/settings.py
import os
from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    
    # Local apps
    'apps.core',
    'apps.users',
    'apps.chats',
]

MIDDLEWARE = [
    # Third party middleware
    'corsheaders.middleware.CorsMiddleware',
    
    # Django built-in middleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom middleware - carefully ordered
    'apps.core.middleware.logging.RequestResponseLoggingMiddleware',  # First custom middleware
    'apps.core.middleware.security.IPBlockingMiddleware',             # Security first
    'apps.core.middleware.security.RateLimitingMiddleware',           # Rate limiting
    'apps.core.middleware.validation.JSONValidationMiddleware',       # Input validation
    'apps.core.middleware.authentication.RoleBasedAccessMiddleware',  # Authorization
    'apps.core.middleware.authentication.MaintenanceModeMiddleware',  # Maintenance mode
    'apps.core.middleware.validation.ContentSecurityMiddleware',      # Security headers last
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Custom middleware configuration
BANNED_IPS = config('BANNED_IPS', default='').split(',')
SUSPICIOUS_HEADERS = {
    'HTTP_USER_AGENT': r'(bot|crawler|scanner|sqlmap|nmap)',
}

RATE_LIMITS = {
    'default': {'requests': 100, 'window': 3600},
    'auth': {'requests': 5, 'window': 300},
    'messages': {'requests': 10, 'window': 60},
    'api': {'requests': 1000, 'window': 3600},
}

ROLE_ACCESS_CONFIG = {
    'admin': {
        'allowed_paths': ['*'],
        'allowed_methods': ['*'],
    },
    'moderator': {
        'allowed_paths': ['/api/', '/admin/core/', '/admin/chats/'],
        'allowed_methods': ['GET', 'POST', 'PUT', 'PATCH'],
        'denied_methods': ['DELETE']
    },
    'user': {
        'allowed_paths': ['/api/chats/', '/api/conversations/', '/api/messages/'],
        'allowed_methods': ['GET', 'POST'],
        'denied_paths': ['/admin/', '/api/admin/']
    }
}

# Maintenance mode
MAINTENANCE_MODE = config('MAINTENANCE_MODE', default=False, cast=bool)
MAINTENANCE_ETA = '30 minutes'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Cache configuration for rate limiting
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} - {name} - {levelname} - {message}',
            'style': '{',
        },
        'simple': {
            'format': '{asctime} - {message}',
            'style': '{',
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'api_requests.log',
            'formatter': 'json',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'security.log',
            'formatter': 'json',
        },
    },
    'loggers': {
        'request_logger': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.core.middleware': {
            'handlers': ['console', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}