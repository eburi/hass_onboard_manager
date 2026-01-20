# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-20

### Added
- Initial release of Onboard Manager integration
- Automatic Home Assistant user discovery and sync
- Per-user control entities:
  - Onboard switch
  - Notify switch
  - Role selector
  - Notifiers sensor
- Aggregate sensors for active notifiers (all users and per-role)
- Notification group entities:
  - Per-user notify groups (`notify.onboard_manager_user_*`)
  - All active users group (`notify.onboard_manager_all`)
  - Per-role groups (`notify.onboard_manager_role_*`)
- Services:
  - `onboard_manager.set_user` - Update user settings
  - `onboard_manager.set_user_notifiers` - Manage user notifiers
  - `onboard_manager.reload_users` - Force user sync
  - `onboard_manager.export_state` - Export current state
- Persistent storage via Home Assistant storage system
- Role management via config flow and options flow
- Automatic entity creation/removal on user changes
- Dynamic role updates with user reassignment
- HACS compatibility
- Comprehensive documentation and examples
- Alert2 integration examples

### Features
- 5-minute automatic user sync interval
- Support for multiple notifiers per user
- Notifier list modes: replace, add, remove
- User lookup by user_id or username
- Automatic notifier normalization (ensures `notify.` prefix)
- Active user concept (onboard + notify flags)
- Deduplicated notifier lists in aggregates
- Graceful handling of user addition/removal
- Role slug generation from labels
- Stable entity IDs using short user ID

### Technical
- Implements DataUpdateCoordinator pattern
- Uses CoordinatorEntity for all entities
- Proper async/await patterns throughout
- Comprehensive error handling and logging
- Clean separation of concerns across modules
- Follows Home Assistant integration best practices
- Type hints throughout codebase
