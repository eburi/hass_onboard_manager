"""The Onboard Manager integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import OnboardManagerCoordinator
from .services import register_services, unregister_services
from .storage import OnboardStorage

_LOGGER = logging.getLogger(__name__)


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
        # Remove config entry data
        hass.data[DOMAIN].pop(entry.entry_id)

        # Unregister services if this was the last entry
        if not hass.data[DOMAIN]:
            unregister_services(hass)

    return unload_ok
