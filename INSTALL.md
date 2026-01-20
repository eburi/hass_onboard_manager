# Quick Installation Guide

## Prerequisites
- Home Assistant 2023.8 or newer
- At least one Home Assistant user account

## Installation Steps

### Method 1: Manual Installation

1. **Download the integration**
   ```bash
   cd /config
   mkdir -p custom_components
   cd custom_components
   git clone https://github.com/eburi/hass_onboard_manager.git onboard_manager
   ```
   
   Or manually copy the `custom_components/onboard_manager` directory to your Home Assistant `config/custom_components/` directory.

2. **Restart Home Assistant**
   - Go to Settings → System → Restart
   - Or use the command: `ha core restart` (if using Home Assistant OS)

3. **Add the integration**
   - Go to Settings → Devices & Services
   - Click "+ Add Integration"
   - Search for "Onboard Manager"
   - Click on it to start setup

4. **Configure roles**
   - Enter roles as comma-separated values
   - Example: `Crew, Passenger, Guest`
   - Click Submit

5. **Verify installation**
   - Check that entities were created for each user
   - Look for entities like:
     - `switch.onboard_manager_onboard_*`
     - `switch.onboard_manager_notify_*`
     - `select.onboard_manager_role_*`
     - `sensor.onboard_manager_notifiers_*`
     - `notify.onboard_manager_all`

### Method 2: HACS Installation (Coming Soon)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots in the top right
4. Select "Custom repositories"
5. Add: `https://github.com/eburi/hass_onboard_manager`
6. Category: Integration
7. Click "Add"
8. Find "Onboard Manager" in the list
9. Click "Download"
10. Restart Home Assistant
11. Add integration via Settings → Devices & Services

## Initial Configuration

### Set Up User Notifiers

For each user, configure their notification services:

```yaml
# In Developer Tools → Services
service: onboard_manager.set_user_notifiers
data:
  username: anna  # Or use user_id
  notifiers:
    - notify.mobile_app_anna
    - notify.telegram_anna
```

### Set User Onboard Status

Control who is "onboard" (active):

```yaml
service: onboard_manager.set_user
data:
  username: anna
  onboard: true
  notify: true
  role: crew
```

Or use the UI switches:
- `switch.onboard_manager_onboard_*` - Toggle onboard status
- `switch.onboard_manager_notify_*` - Toggle notifications

### Assign Roles

Use the select entity or service:

```yaml
service: onboard_manager.set_user
data:
  username: anna
  role: crew
```

## First Automation Example

Send a notification to all active users:

```yaml
automation:
  - alias: "Test Notification"
    trigger:
      - platform: state
        entity_id: input_boolean.test_trigger
        to: "on"
    action:
      - service: notify.onboard_manager_all
        data:
          message: "This is a test notification!"
          title: "Test"
```

## Verification Checklist

- [ ] Integration appears in Settings → Devices & Services
- [ ] Entities created for each Home Assistant user
- [ ] Aggregate sensors created (all and per-role)
- [ ] Notification groups created
- [ ] Services available in Developer Tools
- [ ] No errors in Home Assistant logs
- [ ] Storage file created: `.storage/onboard_manager`

## Common First-Time Issues

### No entities appear
- **Solution**: Check that you have at least one active HA user
- Run: `onboard_manager.reload_users` service

### Can't find integration in Add Integration
- **Solution**: Restart Home Assistant after copying files
- Check that files are in `config/custom_components/onboard_manager/`

### Entities show as "unavailable"
- **Solution**: User may have been deleted from HA
- Run: `onboard_manager.reload_users` service

### Notifications not being sent
- **Solution**: 
  1. Set notifiers for the user
  2. Enable notify switch
  3. For aggregate groups, also enable onboard switch
  4. Verify underlying notify services exist

## Next Steps

1. **Configure all users**
   - Set notifiers for each user
   - Assign appropriate roles
   - Set onboard status

2. **Test notification groups**
   - Send test messages via Developer Tools
   - Verify messages reach correct notifiers

3. **Create automations**
   - Use notification groups in automations
   - Leverage active notifier sensors for Alert2

4. **Optional: Create dashboard**
   - Display onboard roster
   - Quick controls for user status

## Getting Help

- **Documentation**: See `README.md` for complete guide
- **Testing**: See `TESTING.py` for test cases
- **Issues**: Report on GitHub issues
- **Logs**: Enable debug logging:
  ```yaml
  logger:
    logs:
      custom_components.onboard_manager: debug
  ```

## Uninstallation

1. Remove integration from Settings → Devices & Services
2. Restart Home Assistant
3. Delete `custom_components/onboard_manager` directory
4. Delete `.storage/onboard_manager` file (optional, for clean removal)
