"""Switch platform for Onboard Manager."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_PREFIX
from .coordinator import OnboardManagerCoordinator
from .user_registry import get_short_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Onboard Manager switches."""
    coordinator: OnboardManagerCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities: list[SwitchEntity] = []

    # Create per-user switches
    for user_id, user_data in coordinator.data["users"].items():
        entities.append(OnboardSwitch(coordinator, config_entry, user_id))
        entities.append(NotifySwitch(coordinator, config_entry, user_id))

    async_add_entities(entities)

    # Register platform update callback to handle user additions/removals
    @callback
    def async_add_remove_entities() -> None:
        """Add or remove entities based on coordinator data."""
        current_users = coordinator.data.get("users", {})

        # Get existing entity user IDs
        existing_user_ids = {
            entity.user_id
            for entity in entities
            if hasattr(entity, "user_id")
        }

        new_entities = []

        # Add switches for new users
        for user_id in current_users:
            if user_id not in existing_user_ids:
                new_entities.append(OnboardSwitch(coordinator, config_entry, user_id))
                new_entities.append(NotifySwitch(coordinator, config_entry, user_id))

        if new_entities:
            async_add_entities(new_entities)
            entities.extend(new_entities)

    # Listen for coordinator updates
    config_entry.async_on_unload(
        coordinator.async_add_listener(async_add_remove_entities)
    )


class OnboardSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to control user's onboard status."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
        user_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.user_id = user_id
        self._attr_has_entity_name = False

        short_id = get_short_id(user_id)
        self._attr_unique_id = f"{config_entry.entry_id}_{user_id}_onboard"

        # Set entity_id suggestion
        self.entity_id = f"switch.{ENTITY_PREFIX}_onboard_{short_id}"

        self._update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        super()._handle_coordinator_update()

    def _update_attrs(self) -> None:
        """Update switch attributes."""
        user_data = self.coordinator.data["users"].get(self.user_id, {})

        if not user_data:
            # User no longer exists
            self._attr_available = False
            return

        self._attr_available = True
        name = user_data.get("name", "Unknown")

        self._attr_name = f"{name} Onboard"
        self._attr_is_on = user_data.get("onboard", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_update_user(self.user_id, {"onboard": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_update_user(self.user_id, {"onboard": False})


class NotifySwitch(CoordinatorEntity, SwitchEntity):
    """Switch to control user's notify status."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
        user_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.user_id = user_id
        self._attr_has_entity_name = False

        short_id = get_short_id(user_id)
        self._attr_unique_id = f"{config_entry.entry_id}_{user_id}_notify"

        # Set entity_id suggestion
        self.entity_id = f"switch.{ENTITY_PREFIX}_notify_{short_id}"

        self._update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        super()._handle_coordinator_update()

    def _update_attrs(self) -> None:
        """Update switch attributes."""
        user_data = self.coordinator.data["users"].get(self.user_id, {})

        if not user_data:
            # User no longer exists
            self._attr_available = False
            return

        self._attr_available = True
        name = user_data.get("name", "Unknown")

        self._attr_name = f"Notify {name}"
        self._attr_is_on = user_data.get("notify", True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_update_user(self.user_id, {"notify": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_update_user(self.user_id, {"notify": False})
