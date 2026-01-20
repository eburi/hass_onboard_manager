"""Select platform for Onboard Manager."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
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
    """Set up Onboard Manager selects."""
    coordinator: OnboardManagerCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities: list[SelectEntity] = []

    # Create per-user role selects
    for user_id, user_data in coordinator.data["users"].items():
        entities.append(RoleSelect(coordinator, config_entry, user_id))

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
            if isinstance(entity, RoleSelect)
        }

        new_entities = []

        # Add selects for new users
        for user_id in current_users:
            if user_id not in existing_user_ids:
                new_entities.append(RoleSelect(coordinator, config_entry, user_id))

        if new_entities:
            async_add_entities(new_entities)
            entities.extend(new_entities)

    # Listen for coordinator updates
    config_entry.async_on_unload(
        coordinator.async_add_listener(async_add_remove_entities)
    )


class RoleSelect(CoordinatorEntity, SelectEntity):
    """Select entity to choose user's role."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
        user_id: str,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self.user_id = user_id
        self._attr_has_entity_name = False

        short_id = get_short_id(user_id)
        self._attr_unique_id = f"{config_entry.entry_id}_{user_id}_role"

        # Set entity_id suggestion
        self.entity_id = f"select.{ENTITY_PREFIX}_role_{short_id}"

        self._update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        super()._handle_coordinator_update()

    def _update_attrs(self) -> None:
        """Update select attributes."""
        user_data = self.coordinator.data["users"].get(self.user_id, {})

        if not user_data:
            # User no longer exists
            self._attr_available = False
            return

        self._attr_available = True
        name = user_data.get("name", "Unknown")

        self._attr_name = f"{name} Role"

        # Get role options from coordinator
        roles = self.coordinator.data.get("roles", [])
        self._attr_options = [role["label"] for role in roles]

        # Get current role and convert slug to label
        current_role_slug = user_data.get("role", "")
        current_role_label = current_role_slug
        for role in roles:
            if role["slug"] == current_role_slug:
                current_role_label = role["label"]
                break

        self._attr_current_option = current_role_label

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Convert label to slug
        roles = self.coordinator.data.get("roles", [])
        role_slug = None
        for role in roles:
            if role["label"] == option:
                role_slug = role["slug"]
                break

        if role_slug:
            await self.coordinator.async_update_user(self.user_id, {"role": role_slug})
        else:
            _LOGGER.error(f"Invalid role selected: {option}")
