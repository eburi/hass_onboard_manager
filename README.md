# Onboard Manager for Home Assistant

A Home Assistant custom integration that manages an "onboard roster" keyed by HA Users and automatically keeps entities and notification groups in sync as users are added/removed.

## Features

- **Automatic User Discovery**: Automatically discovers and syncs Home Assistant users
- **Per-User Control Entities**: Creates onboard/notify switches, role selector, and notifiers sensor for each user
- **Aggregate Sensors**: Provides sensors listing active notifiers for all users or by role
- **Notification Groups**: Creates `notify.*` services for users, roles, and all active users
- **Persistent Storage**: All data persists via integration storage (no YAML helpers needed)
- **Role Management**: Define custom roles with easy configuration

## Installation

### Manual Installation

1. Copy the `custom_components/onboard_manager` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Onboard Manager"

### HACS Installation

_(Coming soon)_

## Configuration

### Initial Setup

1. Add the integration via the UI
2. Enter roles as comma-separated values (e.g., "Crew, Passenger, Guest")
3. The integration will automatically:
   - Discover all Home Assistant users
   - Create entities for each user
   - Create notification groups

### Managing Roles

To edit roles after setup:

1. Go to Settings → Devices & Services
2. Find "Onboard Manager" and click "Configure"
3. Edit the roles (comma-separated)
4. Users assigned to removed roles will be reassigned to the first role

## Entities Created

### Per-User Entities

For each Home Assistant user, the following entities are created:

- `switch.onboard_manager_onboard_<shortid>` - Controls if user is onboard
- `switch.onboard_manager_notify_<shortid>` - Controls if user receives notifications
- `select.onboard_manager_role_<shortid>` - Select user's role
- `sensor.onboard_manager_notifiers_<shortid>` - Lists user's configured notifiers

### Aggregate Sensors

- `sensor.onboard_manager_active_notifiers_all` - All active notifiers (onboard + notify enabled)
- `sensor.onboard_manager_active_notifiers_role_<role>` - Active notifiers per role

### Notification Groups

- `notify.onboard_manager_user_<shortid>` - Send to specific user's notifiers
- `notify.onboard_manager_all` - Send to all active users
- `notify.onboard_manager_role_<role>` - Send to all active users in a role

**Active users** = users with both `onboard` and `notify` switches enabled.

## Services

### `onboard_manager.set_user`

Update user settings.

**Fields:**
- `user_id` (optional): Home Assistant user ID
- `username` (optional): Username (alternative to user_id)
- `onboard` (optional): Boolean - set onboard status
- `notify` (optional): Boolean - enable/disable notifications
- `role` (optional): String - role slug or label

**Example:**
```yaml
service: onboard_manager.set_user
data:
  username: anna
  onboard: true
  notify: true
  role: crew
```

### `onboard_manager.set_user_notifiers`

Manage user's notification services.

**Fields:**
- `user_id` (optional): Home Assistant user ID
- `username` (optional): Username (alternative to user_id)
- `notifiers` (required): List or comma-separated string of notifier services
- `mode` (optional): `replace` (default), `add`, or `remove`

**Example (Replace):**
```yaml
service: onboard_manager.set_user_notifiers
data:
  username: anna
  notifiers:
    - notify.mobile_app_anna
    - notify.telegram_anna
  mode: replace
```

**Example (Add):**
```yaml
service: onboard_manager.set_user_notifiers
data:
  username: anna
  notifiers: "notify.email_anna"
  mode: add
```

**Example (Remove):**
```yaml
service: onboard_manager.set_user_notifiers
data:
  username: anna
  notifiers: "notify.telegram_anna"
  mode: remove
```

### `onboard_manager.reload_users`

Force re-sync of Home Assistant users.

**Example:**
```yaml
service: onboard_manager.reload_users
```

### `onboard_manager.export_state`

Export current state via service response (for debugging).

**Example:**
```yaml
service: onboard_manager.export_state
response_variable: state
```

## Usage Examples

### Using Notification Groups in Automations

Send a notification to all active crew members:

```yaml
automation:
  - alias: "Alert Crew"
    trigger:
      - platform: state
        entity_id: binary_sensor.intrusion_detected
        to: "on"
    action:
      - service: notify.onboard_manager_role_crew
        data:
          message: "Intrusion detected!"
          title: "Security Alert"
```

Send to a specific user:

```yaml
automation:
  - alias: "Notify Anna"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: notify.onboard_manager_user_a1b2c3d4
        data:
          message: "Good morning!"
```

Send to all active users:

```yaml
automation:
  - alias: "Broadcast Message"
    trigger:
      - platform: state
        entity_id: binary_sensor.fire_alarm
        to: "on"
    action:
      - service: notify.onboard_manager_all
        data:
          message: "Fire alarm activated!"
          title: "EMERGENCY"
```

### Using with Alert2

Use the aggregate sensors for Alert2 notifier lists:

```yaml
alert2:
  intrusion_alert:
    name: "Intrusion Alert"
    condition: binary_sensor.intrusion_detected
    notifiers:
      - notifier: "{{ state_attr('sensor.onboard_manager_active_notifiers_all', 'notifiers') }}"
    reminders:
      - minutes: [5, 10, 15]
```

Or for a specific role:

```yaml
alert2:
  maintenance_alert:
    name: "Maintenance Required"
    condition: binary_sensor.maintenance_needed
    notifiers:
      - notifier: "{{ state_attr('sensor.onboard_manager_active_notifiers_role_crew', 'notifiers') }}"
```

### Setting Up User Notifiers

Use the service to configure which notification services a user should receive:

```yaml
script:
  setup_anna_notifiers:
    sequence:
      - service: onboard_manager.set_user_notifiers
        data:
          username: anna
          notifiers:
            - notify.mobile_app_anna_phone
            - notify.telegram_anna
            - notify.email_anna
```

### Managing Onboard Status

Create a dashboard to manage who is onboard:

```yaml
type: entities
title: Onboard Roster
entities:
  - entity: switch.onboard_manager_onboard_a1b2c3d4
  - entity: switch.onboard_manager_onboard_b2c3d4e5
  - entity: switch.onboard_manager_onboard_c3d4e5f6
```

## Data Model

### Storage Structure

Data is stored in `.storage/onboard_manager`:

```json
{
  "roles": [
    {"label": "Crew", "slug": "crew"},
    {"label": "Passenger", "slug": "passenger"}
  ],
  "users": {
    "<user_id>": {
      "user_id": "<user_id>",
      "name": "Anna",
      "onboard": true,
      "notify": true,
      "role": "crew",
      "notifiers": ["notify.mobile_app_anna", "notify.telegram_anna"]
    }
  }
}
```

### Default Values for New Users

When a new Home Assistant user is detected:
- `onboard`: `false`
- `notify`: `true`
- `role`: First configured role
- `notifiers`: `[]` (empty list)

## Behavior Details

### User Sync

The integration syncs with Home Assistant users:
- **Every 5 minutes** (automatic via coordinator)
- **On integration startup**
- **When `reload_users` service is called**

When users are removed from Home Assistant, their entities are automatically removed.

### Active Notifiers

A user's notifiers are included in "active" lists when:
- `onboard` switch is **ON**
- `notify` switch is **ON**

### Notification Group Behavior

- **User groups** (`notify.onboard_manager_user_*`): Respect the `notify` flag but ignore `onboard`
- **Role groups** (`notify.onboard_manager_role_*`): Only include active users (both flags enabled)
- **All group** (`notify.onboard_manager_all`): Only include active users (both flags enabled)

### Role Updates

When roles are modified:
- Users with invalid roles are reassigned to the first role
- New role notification groups and sensors are created automatically
- Removed role entities become unavailable

## Troubleshooting

### Entities not appearing

1. Check that Home Assistant users exist and are active
2. Run `onboard_manager.reload_users` service
3. Check logs for errors

### Notifications not being sent

1. Verify the user's `notify` switch is ON
2. For aggregate groups, verify `onboard` switch is also ON
3. Check that notifiers are configured: `sensor.onboard_manager_notifiers_*`
4. Verify the underlying notify services exist and work

### Role changes not taking effect

1. Use the integration's options flow (Configure button)
2. After saving, the coordinator will automatically update
3. Check that users were reassigned correctly

## Development

### File Structure

```
custom_components/onboard_manager/
├── __init__.py           # Integration entry point
├── manifest.json         # Integration metadata
├── const.py             # Constants
├── config_flow.py       # Config/options flow
├── coordinator.py       # Data update coordinator
├── storage.py           # Storage management
├── user_registry.py     # User sync and utilities
├── services.py          # Service handlers
├── sensor.py            # Sensor platform
├── switch.py            # Switch platform
├── select.py            # Select platform
├── notify.py            # Notify platform
├── services.yaml        # Service definitions
├── strings.json         # UI strings
└── translations/
    └── en.json          # English translations
```

## License

MIT License - See LICENSE file for details

## Credits

Created by eburi for the hass-onboard-manager project.
