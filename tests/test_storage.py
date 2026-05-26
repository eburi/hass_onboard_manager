"""Tests for storage module."""

from __future__ import annotations

from unittest.mock import patch


from homeassistant.core import HomeAssistant

from custom_components.onboard_manager.storage import OnboardStorage


async def test_storage_load_empty(hass: HomeAssistant) -> None:
    """Test loading empty storage returns defaults."""
    storage = OnboardStorage(hass)
    with patch.object(storage._store, "async_load", return_value=None):
        data = await storage.async_load()
    assert data == {"roles": [], "users": {}}


async def test_storage_load_existing(hass: HomeAssistant) -> None:
    """Test loading existing data from storage."""
    existing = {
        "roles": [{"label": "Crew", "slug": "crew"}],
        "users": {
            "u1": {
                "name": "Alice",
                "notifiers": ["notify.telegram_alice", "notify.mobile_app_alice"],
                "auto_notifiers": ["notify.mobile_app_alice"],
            }
        },
    }
    storage = OnboardStorage(hass)
    with patch.object(storage._store, "async_load", return_value=existing):
        data = await storage.async_load()
    assert data["roles"] == existing["roles"]
    assert data["users"]["u1"]["manual_notifiers"] == ["notify.telegram_alice"]
    assert data["users"]["u1"]["auto_notifiers"] == ["notify.mobile_app_alice"]
    assert data["users"]["u1"]["notifiers"] == [
        "notify.telegram_alice",
        "notify.mobile_app_alice",
    ]


async def test_storage_save(hass: HomeAssistant) -> None:
    """Test saving data to storage."""
    storage = OnboardStorage(hass)
    storage._data = {"roles": [], "users": {"u1": {"name": "Alice"}}}
    with patch.object(storage._store, "async_save") as mock_save:
        await storage.async_save()
        mock_save.assert_called_once_with(storage._data)


def test_storage_get_data(hass: HomeAssistant) -> None:
    """Test getting current data."""
    storage = OnboardStorage(hass)
    assert storage.get_data() == {"roles": [], "users": {}}


def test_storage_update_data(hass: HomeAssistant) -> None:
    """Test updating data."""
    storage = OnboardStorage(hass)
    new_data = {"roles": [{"label": "Crew", "slug": "crew"}], "users": {}}
    storage.update_data(new_data)
    assert storage.get_data() == new_data


def test_storage_roles(hass: HomeAssistant) -> None:
    """Test get/set roles."""
    storage = OnboardStorage(hass)
    assert storage.get_roles() == []
    roles = [{"label": "Crew", "slug": "crew"}]
    storage.set_roles(roles)
    assert storage.get_roles() == roles


def test_storage_user_operations(hass: HomeAssistant) -> None:
    """Test user CRUD operations."""
    storage = OnboardStorage(hass)

    # Set user
    storage.set_user("u1", {"name": "Alice", "onboard": True})
    assert storage.get_user("u1") == {
        "name": "Alice",
        "onboard": True,
        "manual_notifiers": [],
        "auto_notifiers": [],
        "notifiers": [],
    }
    assert storage.get_users() == {
        "u1": {
            "name": "Alice",
            "onboard": True,
            "manual_notifiers": [],
            "auto_notifiers": [],
            "notifiers": [],
        }
    }

    # Update user
    storage.update_user("u1", {"notify": True})
    assert storage.get_user("u1") == {
        "name": "Alice",
        "onboard": True,
        "notify": True,
        "manual_notifiers": [],
        "auto_notifiers": [],
        "notifiers": [],
    }

    # Delete user
    storage.delete_user("u1")
    assert storage.get_user("u1") is None

    # Delete non-existent user (should not raise)
    storage.delete_user("nonexistent")


def test_storage_update_nonexistent_user(hass: HomeAssistant) -> None:
    """Test updating a user that doesn't exist yet creates the record."""
    storage = OnboardStorage(hass)
    storage.update_user("u99", {"name": "New"})
    assert storage.get_user("u99") == {
        "name": "New",
        "manual_notifiers": [],
        "auto_notifiers": [],
        "notifiers": [],
    }
