# config.py
import os

# ============================================================================
# Application Branding
# ============================================================================
APP_NAME = "LDAP Manager"
APP_SHORT_NAME = "LDAP"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Enterprise Directory Management"
COMPANY_NAME = "CoreIP"
COMPANY_LOGO = "coreip-logo.png"  # Place in static/images/
COPYRIGHT_YEAR = "2026"

# ============================================================================
# Brand Colors (Hex codes)
# ============================================================================
BRAND_PRIMARY = "#818cf8"
BRAND_SECONDARY = "#6366f1"
BRAND_PRIMARY_DARK = "#6366f1"
BRAND_PRIMARY_LIGHT = "#818cf8"
BRAND_ACCENT = "#e67e22"
BRAND_SUCCESS = "#22c55e"
BRAND_DANGER = "#ef4444"
BRAND_WARNING = "#f59e0b"

# ============================================================================
# Feature Flags
# ============================================================================
FEATURE_PHONE_LOOKUP = True
FEATURE_IMPORT_EXPORT = True
FEATURE_BULK_DELETE = True
FEATURE_DEBUG = False  # Set to False in production

# ============================================================================
# LDAP Settings (can be overridden by environment variables)
# ============================================================================
LDAP_SERVER = os.getenv('LDAP_SERVER', '127.0.0.1')
LDAP_PORT = int(os.getenv('LDAP_PORT', 1389))
LDAP_BASE = os.getenv('LDAP_BASE', 'dc=coreip,dc=local')
LDAP_ADMIN = os.getenv('LDAP_ADMIN', 'cn=admin,dc=coreip,dc=local')
LDAP_PASSWORD = os.getenv('LDAP_PASSWORD', 'coreip@switch')
PEOPLE_OU = os.getenv('PEOPLE_OU', f"ou=People,{LDAP_BASE}")

# ============================================================================
# Pagination Defaults
# ============================================================================
DEFAULT_PER_PAGE = 25
MAX_PER_PAGE = 100
MIN_PER_PAGE = 10

# ============================================================================
# Session & Security
# ============================================================================
SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
SESSION_TIMEOUT = 3600  # 1 hour

# ============================================================================
# Server Configuration
# ============================================================================
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', 5004))
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() == 'true'

# ============================================================================
# LDAP Advanced Settings
# ============================================================================
LDAP_USE_SSL = os.getenv('LDAP_USE_SSL', 'False').lower() == 'true'
LDAP_SSL_PORT = int(os.getenv('LDAP_SSL_PORT', 636))
LDAP_USE_TLS = os.getenv('LDAP_USE_TLS', 'False').lower() == 'true'
LDAP_CONNECTION_TIMEOUT = int(os.getenv('LDAP_CONNECTION_TIMEOUT', 10))
LDAP_SEARCH_TIMEOUT = int(os.getenv('LDAP_SEARCH_TIMEOUT', 30))

# ============================================================================
# Email Settings (for future notifications)
# ============================================================================
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.company.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_FROM = os.getenv('SMTP_FROM', 'noreply@company.com')

# ============================================================================
# Backup Settings
# ============================================================================
BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'True').lower() == 'true'
BACKUP_DIR = os.getenv('BACKUP_DIR', './backups')
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', 30))

# ============================================================================
# Logging Settings
# ============================================================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'app.log')
LOG_MAX_SIZE_MB = int(os.getenv('LOG_MAX_SIZE_MB', 10))
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))

# ============================================================================
# API Settings
# ============================================================================
API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', 100))  # Requests per minute
API_ENABLED = os.getenv('API_ENABLED', 'True').lower() == 'true'