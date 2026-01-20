"""
Test/Validation checklist for Onboard Manager integration.

This file documents the manual acceptance tests from the requirements.
"""

# Manual Acceptance Tests

## Test 1: Initial Setup
"""
1. Install integration in Home Assistant
2. Go to Settings → Devices & Services → Add Integration
3. Search for "Onboard Manager"
4. Enter roles: "Crew, Passenger, Guest"
5. Complete setup

Expected:
- Integration added successfully
- No errors in logs
"""

## Test 2: Entity Creation
"""
After setup, verify entities exist for each HA user:

For each user (replace <shortid> with first 8 chars of user_id):
- switch.onboard_manager_onboard_<shortid>
- switch.onboard_manager_notify_<shortid>
- select.onboard_manager_role_<shortid>
- sensor.onboard_manager_notifiers_<shortid>
- notify.onboard_manager_user_<shortid>

Aggregate entities:
- notify.onboard_manager_all
- notify.onboard_manager_role_crew
- notify.onboard_manager_role_passenger
- notify.onboard_manager_role_guest
- sensor.onboard_manager_active_notifiers_all
- sensor.onboard_manager_active_notifiers_role_crew
- sensor.onboard_manager_active_notifiers_role_passenger
- sensor.onboard_manager_active_notifiers_role_guest
"""

## Test 3: Set User Notifiers
"""
Call service to set notifiers for a user:

service: onboard_manager.set_user_notifiers
data:
  username: anna
  notifiers:
    - notify.mobile_app_anna
    - notify.telegram_anna

Expected:
- sensor.onboard_manager_notifiers_<shortid> state updates to show list
- No errors in logs
"""

## Test 4: Per-User Notify Group
"""
Call service to send notification to specific user:

service: notify.onboard_manager_user_<shortid>
data:
  message: "Test message for Anna"
  title: "Test"

Expected:
- Both notify.mobile_app_anna and notify.telegram_anna receive the notification
- Check in Home Assistant logs that both services were called
"""

## Test 5: Active Notifiers
"""
1. Set user onboard=true and notify=true:

service: onboard_manager.set_user
data:
  username: anna
  onboard: true
  notify: true

2. Call notify.onboard_manager_all:

service: notify.onboard_manager_all
data:
  message: "Test message to all active users"

Expected:
- Only active users' notifiers receive the notification
- sensor.onboard_manager_active_notifiers_all shows the notifiers
"""

## Test 6: Role-Based Notify Group
"""
1. Ensure user has role set to "crew"
2. Set user onboard=true and notify=true
3. Call notify.onboard_manager_role_crew:

service: notify.onboard_manager_role_crew
data:
  message: "Test message to crew"

Expected:
- User's notifiers receive the notification
- sensor.onboard_manager_active_notifiers_role_crew shows the notifiers
"""

## Test 7: Add New User
"""
1. Add a new user in Home Assistant (Settings → People)
2. Call reload service:

service: onboard_manager.reload_users

Expected:
- New entities created for the new user
- New notify group created
- No errors in logs
"""

## Test 8: Remove User
"""
1. Remove a user from Home Assistant
2. Call reload service:

service: onboard_manager.reload_users

Expected:
- User's entities disappear/become unavailable
- User's notify group disappears
- No errors in logs
"""

## Test 9: Persistence
"""
1. Configure users, roles, notifiers
2. Restart Home Assistant
3. Check all entities and data

Expected:
- All entities remain with correct states
- All user data persisted
- Storage file .storage/onboard_manager exists and contains correct data
"""

## Test 10: Role Management
"""
1. Go to integration Configure (options flow)
2. Change roles to "Admin, User"
3. Save

Expected:
- Users with old roles reassigned to first role (Admin)
- New role entities created
- Old role entities become unavailable
- No errors in logs
"""

## Test 11: Service Validation
"""
Test various service calls:

# Test with username
service: onboard_manager.set_user
data:
  username: anna
  onboard: true

# Test with user_id
service: onboard_manager.set_user
data:
  user_id: <user_id>
  notify: false

# Test notifier modes
service: onboard_manager.set_user_notifiers
data:
  username: anna
  notifiers: "notify.new_service"
  mode: add

service: onboard_manager.set_user_notifiers
data:
  username: anna
  notifiers: ["notify.mobile_app_anna"]
  mode: remove

# Test export
service: onboard_manager.export_state
response_variable: state

Expected:
- All service calls work correctly
- Data updates as expected
- export_state returns complete state
"""

## Test 12: Integration with Alert2
"""
Create an Alert2 config using the aggregate sensors:

alert2:
  test_alert:
    name: "Test Alert"
    condition: input_boolean.test_trigger
    notifiers:
      - notifier: "{{ state_attr('sensor.onboard_manager_active_notifiers_all', 'notifiers') }}"

Trigger the alert.

Expected:
- Alert2 can parse the notifier list
- Notifications sent to all active users
"""

# Implementation Validation Checklist

IMPLEMENTATION_CHECKLIST = {
    "Core Structure": [
        "✓ manifest.json with correct domain and platforms",
        "✓ const.py with all constants",
        "✓ strings.json and translations/en.json",
        "✓ services.yaml with service definitions",
    ],
    "Storage": [
        "✓ storage.py implements OnboardStorage",
        "✓ Uses homeassistant.helpers.storage.Store",
        "✓ Storage key: onboard_manager, version 1",
        "✓ Stores roles and users dict",
    ],
    "User Registry": [
        "✓ user_registry.py with sync logic",
        "✓ get_short_id() for stable entity suffixes",
        "✓ normalize_notifier() ensures notify. prefix",
        "✓ parse_notifiers_input() handles list/string",
        "✓ get_ha_users() filters system users",
        "✓ sync_users() adds/updates/removes users",
        "✓ compute_active_notifiers() aggregates lists",
        "✓ resolve_user_id() handles username lookup",
    ],
    "Coordinator": [
        "✓ coordinator.py extends DataUpdateCoordinator",
        "✓ 5-minute update interval",
        "✓ Syncs users on each update",
        "✓ Computes active notifiers aggregates",
        "✓ Provides async_update_user()",
        "✓ Provides async_update_roles()",
        "✓ Provides async_reload_users()",
    ],
    "Config Flow": [
        "✓ config_flow.py with setup and options",
        "✓ parse_roles() creates slug from label",
        "✓ Validates at least one role required",
        "✓ Options flow allows editing roles",
        "✓ Updates coordinator on role changes",
    ],
    "Platforms": [
        "✓ sensor.py: per-user notifiers + aggregates",
        "✓ switch.py: onboard + notify switches",
        "✓ select.py: role picker",
        "✓ notify.py: user/all/role notify entities",
        "✓ All platforms use CoordinatorEntity",
        "✓ Dynamic entity addition/removal",
    ],
    "Services": [
        "✓ services.py registers all services",
        "✓ set_user: updates onboard/notify/role",
        "✓ set_user_notifiers: replace/add/remove modes",
        "✓ reload_users: forces sync",
        "✓ export_state: returns service response",
        "✓ Proper validation and error handling",
    ],
    "Entry Point": [
        "✓ __init__.py setup and unload",
        "✓ Creates storage and coordinator",
        "✓ Forwards platform setups",
        "✓ Registers services",
        "✓ Proper cleanup on unload",
    ],
    "Documentation": [
        "✓ README.md with full documentation",
        "✓ Installation instructions",
        "✓ Entity descriptions",
        "✓ Service examples",
        "✓ Alert2 integration examples",
        "✓ Troubleshooting section",
    ],
    "Additional Files": [
        "✓ LICENSE (MIT)",
        "✓ .gitignore",
        "✓ hacs.json for HACS compatibility",
    ],
}

# Entity ID Examples (for user_id starting with a1b2c3d4...)
ENTITY_EXAMPLES = {
    "switches": [
        "switch.onboard_manager_onboard_a1b2c3d4",
        "switch.onboard_manager_notify_a1b2c3d4",
    ],
    "selects": [
        "select.onboard_manager_role_a1b2c3d4",
    ],
    "sensors": [
        "sensor.onboard_manager_notifiers_a1b2c3d4",
        "sensor.onboard_manager_active_notifiers_all",
        "sensor.onboard_manager_active_notifiers_role_crew",
    ],
    "notify": [
        "notify.onboard_manager_user_a1b2c3d4",
        "notify.onboard_manager_all",
        "notify.onboard_manager_role_crew",
    ],
}
