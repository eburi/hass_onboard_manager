"""Tests for user_registry module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser


from custom_components.onboard_manager.user_registry import (
    compute_active_notifiers,
    compute_active_notifiers_by_role,
    get_short_id,
    normalize_notifier,
    parse_notifiers_input,
    sync_users,
)


def test_get_short_id() -> None:
    """Test short ID extraction."""
    assert get_short_id("abcdefghijklmnop") == "abcdefgh"
    assert get_short_id("12345678") == "12345678"


def test_normalize_notifier() -> None:
    """Test notifier normalization."""
    assert normalize_notifier("mobile_app_alice") == "notify.mobile_app_alice"
    assert normalize_notifier("notify.mobile_app_alice") == "notify.mobile_app_alice"
    assert normalize_notifier("  mobile_app_bob  ") == "notify.mobile_app_bob"
    assert normalize_notifier("  notify.foo  ") == "notify.foo"


def test_parse_notifiers_input_string() -> None:
    """Test parsing comma-separated string input."""
    result = parse_notifiers_input("mobile_app_alice, notify.mobile_app_bob")
    assert result == ["notify.mobile_app_alice", "notify.mobile_app_bob"]


def test_parse_notifiers_input_list() -> None:
    """Test parsing list input."""
    result = parse_notifiers_input(["mobile_app_alice", "notify.mobile_app_bob"])
    assert result == ["notify.mobile_app_alice", "notify.mobile_app_bob"]


def test_parse_notifiers_input_empty_string() -> None:
    """Test parsing empty string."""
    assert parse_notifiers_input("") == []


def test_parse_notifiers_input_invalid_type() -> None:
    """Test parsing invalid type returns empty list."""
    assert parse_notifiers_input(123) == []


def test_compute_active_notifiers(
    mock_users: dict[str, dict[str, Any]],
) -> None:
    """Test computing active notifiers for all users.

    Alice: onboard=True, notify=True -> included
    Bob: onboard=False, notify=True -> excluded (not onboard)
    Charlie: onboard=True, notify=False -> excluded (notify off)
    """
    result = compute_active_notifiers(mock_users)
    assert result == ["notify.mobile_app_alice"]


def test_compute_active_notifiers_empty() -> None:
    """Test computing active notifiers with no users."""
    assert compute_active_notifiers({}) == []


def test_compute_active_notifiers_deduplication() -> None:
    """Test that duplicate notifiers are deduplicated."""
    users = {
        "u1": {
            "onboard": True,
            "notify": True,
            "notifiers": ["notify.shared"],
        },
        "u2": {
            "onboard": True,
            "notify": True,
            "notifiers": ["notify.shared"],
        },
    }
    result = compute_active_notifiers(users)
    assert result == ["notify.shared"]


def test_compute_active_notifiers_by_role(
    mock_users: dict[str, dict[str, Any]],
) -> None:
    """Test computing active notifiers grouped by role.

    Only Alice (crew, onboard, notify) qualifies.
    """
    result = compute_active_notifiers_by_role(mock_users)
    assert result == {"crew": ["notify.mobile_app_alice"]}


def test_compute_active_notifiers_by_role_empty() -> None:
    """Test computing active notifiers by role with no users."""
    assert compute_active_notifiers_by_role({}) == {}


def _create_mobile_app_tracker(
    hass,
    *,
    webhook_id: str,
    device_name: str,
    suggested_object_id: str,
) -> tuple[MockConfigEntry, str]:
    """Create a mock mobile_app device and device_tracker entity."""
    config_entry = MockConfigEntry(
        domain="mobile_app",
        entry_id=f"entry_{webhook_id}",
        title=device_name,
        data={"device_name": device_name, "user_id": "user_aaa"},
    )
    config_entry.add_to_hass(hass)

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("mobile_app", f"device_{webhook_id}")},
        name=device_name,
    )

    entity_entry = er.async_get(hass).async_get_or_create(
        "device_tracker",
        "mobile_app",
        f"tracker_{webhook_id}",
        suggested_object_id=suggested_object_id,
        config_entry=config_entry,
        device_id=device.id,
    )

    hass.data.setdefault("mobile_app", {}).setdefault("config_entries", {})[
        webhook_id
    ] = config_entry
    hass.data["mobile_app"].setdefault("devices", {})[webhook_id] = device

    return config_entry, entity_entry.entity_id


async def test_sync_users_auto_syncs_notifiers_from_person_devices(
    hass, mock_roles: list[dict[str, str]]
) -> None:
    """Test device-linked mobile_app notifiers are auto-added to users."""
    hass.auth.async_get_users = AsyncMock(
        return_value=[MockUser(id="user_aaa", name="Alice")]
    )
    hass.data["mobile_app"] = {
        "config_entries": {},
        "devices": {},
        "notify": type(
            "NotifyService",
            (),
            {
                "registered_targets": {
                    "mobile_app_alice_phone": "webhook_phone",
                    "mobile_app_alice_watch": "webhook_watch",
                }
            },
        )(),
    }

    _, phone_tracker = _create_mobile_app_tracker(
        hass,
        webhook_id="webhook_phone",
        device_name="Alice Phone",
        suggested_object_id="alice_phone",
    )
    _, watch_tracker = _create_mobile_app_tracker(
        hass,
        webhook_id="webhook_watch",
        device_name="Alice Watch",
        suggested_object_id="alice_watch",
    )

    hass.states.async_set(
        "person.alice",
        "home",
        {
            "user_id": "user_aaa",
            "device_trackers": [phone_tracker, watch_tracker],
        },
    )

    updated_users, removed_users = await sync_users(
        hass,
        {
            "user_aaa": {
                "user_id": "user_aaa",
                "name": "Alice",
                "onboard": True,
                "notify": True,
                "role": "crew",
                "notifiers": ["notify.telegram_alice"],
            }
        },
        mock_roles,
    )

    assert removed_users == set()
    assert updated_users["user_aaa"]["manual_notifiers"] == ["notify.telegram_alice"]
    assert updated_users["user_aaa"]["auto_notifiers"] == [
        "notify.mobile_app_alice_phone",
        "notify.mobile_app_alice_watch",
    ]
    assert updated_users["user_aaa"]["notifiers"] == [
        "notify.telegram_alice",
        "notify.mobile_app_alice_phone",
        "notify.mobile_app_alice_watch",
    ]


async def test_sync_users_replaces_stale_auto_notifiers(
    hass, mock_roles: list[dict[str, str]]
) -> None:
    """Test auto-synced notifiers follow the current person device list."""
    hass.auth.async_get_users = AsyncMock(
        return_value=[MockUser(id="user_aaa", name="Alice")]
    )
    hass.data["mobile_app"] = {
        "config_entries": {},
        "devices": {},
        "notify": type(
            "NotifyService",
            (),
            {"registered_targets": {"mobile_app_alice_phone": "webhook_phone"}},
        )(),
    }

    _, phone_tracker = _create_mobile_app_tracker(
        hass,
        webhook_id="webhook_phone",
        device_name="Alice Phone",
        suggested_object_id="alice_phone",
    )

    hass.states.async_set(
        "person.alice",
        "home",
        {
            "user_id": "user_aaa",
            "device_trackers": [phone_tracker],
        },
    )

    updated_users, _ = await sync_users(
        hass,
        {
            "user_aaa": {
                "user_id": "user_aaa",
                "name": "Alice",
                "onboard": True,
                "notify": True,
                "role": "crew",
                "notifiers": [
                    "notify.telegram_alice",
                    "notify.mobile_app_old_phone",
                ],
                "auto_notifiers": ["notify.mobile_app_old_phone"],
            }
        },
        mock_roles,
    )

    assert updated_users["user_aaa"]["manual_notifiers"] == ["notify.telegram_alice"]
    assert updated_users["user_aaa"]["auto_notifiers"] == [
        "notify.mobile_app_alice_phone"
    ]
    assert updated_users["user_aaa"]["notifiers"] == [
        "notify.telegram_alice",
        "notify.mobile_app_alice_phone",
    ]
