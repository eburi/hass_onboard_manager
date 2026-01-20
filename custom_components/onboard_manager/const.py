"""Constants for the Onboard Manager integration."""

DOMAIN = "onboard_manager"

# Platforms
PLATFORMS = ["sensor", "switch", "select", "notify"]

# Storage
STORAGE_KEY = "onboard_manager"
STORAGE_VERSION = 1

# Update interval
UPDATE_INTERVAL_SECONDS = 300  # 5 minutes

# Defaults for new users
DEFAULT_ONBOARD = False
DEFAULT_NOTIFY = True
DEFAULT_NOTIFIERS = []

# Service names
SERVICE_SET_USER = "set_user"
SERVICE_SET_USER_NOTIFIERS = "set_user_notifiers"
SERVICE_RELOAD_USERS = "reload_users"
SERVICE_EXPORT_STATE = "export_state"

# Notifier modes
NOTIFIER_MODE_REPLACE = "replace"
NOTIFIER_MODE_ADD = "add"
NOTIFIER_MODE_REMOVE = "remove"

# Entity prefixes
ENTITY_PREFIX = "onboard_manager"
