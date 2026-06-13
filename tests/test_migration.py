"""Tests for config entry migrations."""

from __future__ import annotations

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.onboard_manager import async_migrate_entry
from custom_components.onboard_manager.const import DOMAIN
from custom_components.onboard_manager.storage import OnboardStorage


async def test_async_migrate_entry_renames_per_user_entities(
    hass, monkeypatch
) -> None:
    """Test entity ids migrate from short ids to username slugs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test-entry",
        version=1,
        data={"roles": [{"label": "Crew", "slug": "crew"}]},
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "switch",
        DOMAIN,
        f"{entry.entry_id}_user_aaa_onboard",
        suggested_object_id="onboard_manager_onboard_9732c8e2",
        config_entry=entry,
    )
    entity_registry.async_get_or_create(
        "switch",
        DOMAIN,
        f"{entry.entry_id}_user_aaa_notify",
        suggested_object_id="onboard_manager_notify_9732c8e2",
        config_entry=entry,
    )
    entity_registry.async_get_or_create(
        "select",
        DOMAIN,
        f"{entry.entry_id}_user_aaa_role",
        suggested_object_id="onboard_manager_role_9732c8e2",
        config_entry=entry,
    )
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_user_aaa_notifiers",
        suggested_object_id="onboard_manager_notifiers_9732c8e2",
        config_entry=entry,
    )
    entity_registry.async_get_or_create(
        "notify",
        DOMAIN,
        f"{entry.entry_id}_user_aaa_notify_group",
        suggested_object_id="onboard_manager_user_9732c8e2",
        config_entry=entry,
    )

    async def _async_load(self: OnboardStorage) -> None:
        self._data = {
            "roles": [{"label": "Crew", "slug": "crew"}],
            "users": {
                "user_aaa": {
                    "user_id": "user_aaa",
                    "name": "Erich Buri",
                }
            },
        }

    monkeypatch.setattr(OnboardStorage, "async_load", _async_load)

    assert await async_migrate_entry(hass, entry) is True
    assert entry.version == 2

    assert entity_registry.async_get("switch.onboard_manager_onboard_erich_buri")
    assert entity_registry.async_get("switch.onboard_manager_notify_erich_buri")
    assert entity_registry.async_get("select.onboard_manager_role_erich_buri")
    assert entity_registry.async_get("sensor.onboard_manager_notifiers_erich_buri")
    assert entity_registry.async_get("notify.onboard_manager_user_erich_buri")

    assert entity_registry.async_get("switch.onboard_manager_onboard_9732c8e2") is None
    assert entity_registry.async_get("switch.onboard_manager_notify_9732c8e2") is None
    assert entity_registry.async_get("select.onboard_manager_role_9732c8e2") is None
    assert entity_registry.async_get("sensor.onboard_manager_notifiers_9732c8e2") is None
    assert entity_registry.async_get("notify.onboard_manager_user_9732c8e2") is None
