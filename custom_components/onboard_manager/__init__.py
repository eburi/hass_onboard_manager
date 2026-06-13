"""The Onboard Manager integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import OnboardManagerCoordinator
from .services import register_services, unregister_services
from .storage import OnboardStorage
from .user_registry import get_short_id, get_user_entity_slug

_LOGGER = logging.getLogger(__name__)

_MIGRATION_SUFFIXES: dict[str, dict[str, str]] = {
    "switch": {"_onboard": "onboard", "_notify": "notify"},
    "select": {"_role": "role"},
    "sensor": {"_notifiers": "notifiers"},
    "notify": {"_notify_group": "user"},
}


def _extract_user_id(unique_id: str, entry_id: str, suffix: str) -> str | None:
    """Extract a user id from a legacy entity unique id."""
    prefix = f"{entry_id}_"
    if not unique_id.startswith(prefix) or not unique_id.endswith(suffix):
        return None

    return unique_id[len(prefix) : -len(suffix)]


async def _migrate_entity_registry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rename legacy entity ids to the readable slug format."""
    storage = OnboardStorage(hass)
    await storage.async_load()
    users: dict[str, dict[str, Any]] = storage.get_data().get("users", {})

    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        suffix_map = _MIGRATION_SUFFIXES.get(entity_entry.domain)
        if not suffix_map:
            continue

        user_id = None
        entity_kind = None
        for unique_suffix, suffix_entity_kind in suffix_map.items():
            user_id = _extract_user_id(
                entity_entry.unique_id, entry.entry_id, unique_suffix
            )
            if user_id is None:
                continue
            entity_kind = suffix_entity_kind
            break

        if not user_id or not entity_kind:
            continue

        user_data = users.get(user_id)
        if not user_data:
            _LOGGER.warning(
                "Skipping migration of %s because user %s is no longer available",
                entity_entry.entity_id,
                user_id,
            )
            continue

        slug = get_user_entity_slug({**user_data, "user_id": user_id})
        new_entity_id = f"{entity_entry.domain}.{DOMAIN}_{entity_kind}_{slug}"

        try:
            entity_registry.async_update_entity(
                entity_entry.entity_id,
                new_entity_id=new_entity_id,
            )
        except ValueError:
            fallback_entity_id = (
                f"{new_entity_id}_{get_short_id(user_id)}"
                if user_id
                else None
            )
            if not fallback_entity_id:
                _LOGGER.warning(
                    "Skipping migration of %s because the target entity id already exists",
                    entity_entry.entity_id,
                )
                continue

            try:
                entity_registry.async_update_entity(
                    entity_entry.entity_id,
                    new_entity_id=fallback_entity_id,
                )
            except ValueError:
                _LOGGER.warning(
                    "Skipping migration of %s because the target entity id already exists",
                    entity_entry.entity_id,
                )
            else:
                _LOGGER.info(
                    "Migrated entity id %s to %s",
                    entity_entry.entity_id,
                    fallback_entity_id,
                )
        else:
            _LOGGER.info(
                "Migrated entity id %s to %s",
                entity_entry.entity_id,
                new_entity_id,
            )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries and entity ids to the current version."""
    if entry.version < 2:
        await _migrate_entity_registry(hass, entry)
        hass.config_entries.async_update_entry(entry, version=2)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Onboard Manager from a config entry."""
    # Initialize storage
    storage = OnboardStorage(hass)
    await storage.async_load()

    # Get roles from config entry
    roles = entry.data.get("roles", [])

    # Initialize storage with roles if not already present
    if not storage.get_roles():
        storage.set_roles(roles)
        await storage.async_save()
    else:
        # Update roles from config entry (in case they changed via options flow)
        storage.set_roles(roles)
        await storage.async_save()

    # Create coordinator
    coordinator = OnboardManagerCoordinator(hass, storage)

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and storage
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "storage": storage,
        "notify_services": [],  # Track registered notify services for cleanup
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (only once, on first setup)
    if len(hass.data[DOMAIN]) == 1:
        register_services(hass, coordinator)

    _LOGGER.info("Onboard Manager integration setup complete")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Unregister legacy notify services created by this entry
        entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
        notify_services = entry_data.get("notify_services", [])
        for service_name in notify_services:
            if hass.services.has_service("notify", service_name):
                hass.services.async_remove("notify", service_name)
                _LOGGER.debug(
                    f"Unregistered legacy notify service: notify.{service_name}"
                )

        # Remove config entry data
        hass.data[DOMAIN].pop(entry.entry_id)

        # Unregister services if this was the last entry
        if not hass.data[DOMAIN]:
            unregister_services(hass)

    return unload_ok
