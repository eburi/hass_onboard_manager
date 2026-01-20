# Contributing to Onboard Manager

Thank you for your interest in contributing to Onboard Manager!

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/eburi/hass_onboard_manager.git
cd hass_onboard_manager
```

2. Install in your Home Assistant development environment:
```bash
# Create symlink in your HA config directory
ln -s $(pwd)/custom_components/onboard_manager /path/to/homeassistant/config/custom_components/onboard_manager
```

3. Restart Home Assistant to load the integration

## Code Structure

```
custom_components/onboard_manager/
├── __init__.py           # Integration entry point and setup
├── config_flow.py        # UI configuration flows
├── const.py             # Constants and configuration
├── coordinator.py       # Data update coordinator
├── storage.py           # Persistent storage management
├── user_registry.py     # User sync and helper functions
├── services.py          # Service registration and handlers
├── sensor.py            # Sensor entities
├── switch.py            # Switch entities
├── select.py            # Select entities
├── notify.py            # Notify entities (notification groups)
├── manifest.json        # Integration metadata
├── services.yaml        # Service definitions for UI
├── strings.json         # UI strings
└── translations/        # Localization files
    └── en.json
```

## Coding Standards

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints for function parameters and return values
- Use f-strings for string formatting
- Add docstrings to all public functions and classes
- Use async/await for all I/O operations
- Follow Home Assistant integration development patterns

## Adding Features

### Adding a New Service

1. Add service constants to `const.py`
2. Define service schema in `services.py`
3. Implement service handler in `services.py`
4. Register service in `register_services()`
5. Add service definition to `services.yaml`
6. Add service strings to `strings.json`
7. Update `README.md` with examples

### Adding a New Platform

1. Create new platform file (e.g., `binary_sensor.py`)
2. Add platform to `PLATFORMS` in `const.py`
3. Implement entity class extending `CoordinatorEntity`
4. Implement `async_setup_entry()` function
5. Add dynamic entity management if needed
6. Update `README.md` documentation

### Modifying Data Model

1. Update storage structure in `storage.py`
2. Increment `STORAGE_VERSION` in `const.py` if breaking changes
3. Add migration logic if needed (for backward compatibility)
4. Update coordinator to handle new data
5. Update affected platforms
6. Update tests and documentation

## Testing

### Manual Testing Checklist

See `TESTING.py` for comprehensive manual test cases.

Key areas to test:
- [ ] User sync on startup
- [ ] User addition/removal
- [ ] Role changes
- [ ] Notifier management
- [ ] Notification group sending
- [ ] Service calls
- [ ] Persistence after restart
- [ ] Config/options flow

### Integration Testing in Home Assistant

1. Clear existing config entry:
```bash
# Stop Home Assistant
# Delete .storage/core.config_entries (or just the onboard_manager entry)
# Delete .storage/onboard_manager
```

2. Start Home Assistant with clean state
3. Add integration via UI
4. Follow manual testing checklist

### Debugging

Enable debug logging in `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.onboard_manager: debug
```

Check logs in Home Assistant:
- Settings → System → Logs
- Or `home-assistant.log` file

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly using manual testing checklist
5. Update documentation (README.md, CHANGELOG.md)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Pull Request Guidelines

- Describe what the PR does and why
- Reference any related issues
- Include testing steps
- Update CHANGELOG.md with changes
- Ensure code follows style guidelines
- Verify no breaking changes (or document them)

## Versioning

We use [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

Update version in:
- `manifest.json`
- `CHANGELOG.md`

## Code Review

All submissions require review. We review PRs for:
- Code quality and style
- Functionality and correctness
- Testing coverage
- Documentation completeness
- Backward compatibility
- Home Assistant best practices

## Common Pitfalls

### Entity ID Stability
- Always use `unique_id` (not `entity_id`)
- Use stable identifiers (user_id, not username)
- Don't force entity_id in entity classes

### Async Patterns
- All I/O must use async/await
- Don't block the event loop
- Use `hass.async_add_executor_job()` for sync operations

### Storage
- Always await storage operations
- Call `async_save()` after data changes
- Don't modify storage dict directly; use helper methods

### Coordinator
- Update coordinator after storage changes
- Use `async_refresh()` to trigger updates
- Let coordinator manage data state

### Services
- Validate all inputs
- Handle errors gracefully
- Log appropriate messages
- Use service response for data return (not state)

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
