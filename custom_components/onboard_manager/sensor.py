"""Sensor platform for Onboard Manager."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
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
    """Set up Onboard Manager sensors."""
    coordinator: OnboardManagerCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities: list[SensorEntity] = []

    # Create per-user notifiers sensors
    for user_id, user_data in coordinator.data["users"].items():
        entities.append(OnboardUserNotifiersSensor(coordinator, config_entry, user_id))

    # Create aggregate sensors
    entities.append(OnboardActiveNotifiersAllSensor(coordinator, config_entry))

    for role in coordinator.data["roles"]:
        entities.append(
            OnboardActiveNotifiersRoleSensor(coordinator, config_entry, role["slug"])
        )

    async_add_entities(entities)

    # Register platform update callback to handle user additions/removals
    @callback
    def async_add_remove_entities() -> None:
        """Add or remove entities based on coordinator data."""
        current_users = coordinator.data.get("users", {})
        current_roles = coordinator.data.get("roles", [])

        # Get existing entity user IDs
        existing_user_ids = {
            entity.user_id
            for entity in entities
            if isinstance(entity, OnboardUserNotifiersSensor)
        }

        # Get existing role slugs
        existing_role_slugs = {
            entity.role_slug
            for entity in entities
            if isinstance(entity, OnboardActiveNotifiersRoleSensor)
        }

        new_entities = []

        # Add sensors for new users
        for user_id in current_users:
            if user_id not in existing_user_ids:
                new_entities.append(
                    OnboardUserNotifiersSensor(coordinator, config_entry, user_id)
                )

        # Add sensors for new roles
        current_role_slugs = {role["slug"] for role in current_roles}
        for role_slug in current_role_slugs:
            if role_slug not in existing_role_slugs:
                new_entities.append(
                    OnboardActiveNotifiersRoleSensor(
                        coordinator, config_entry, role_slug
                    )
                )

        if new_entities:
            async_add_entities(new_entities)
            entities.extend(new_entities)

    # Listen for coordinator updates
    config_entry.async_on_unload(
        coordinator.async_add_listener(async_add_remove_entities)
    )


class OnboardUserNotifiersSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing notifiers configured for a specific user."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
        user_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.user_id = user_id
        self._attr_has_entity_name = False

        short_id = get_short_id(user_id)
        self._attr_unique_id = f"{config_entry.entry_id}_{user_id}_notifiers"
        self._attr_name = None  # Will be set in _update_attrs

        # Set entity_id suggestion
        user_data = coordinator.data["users"].get(user_id, {})
        name = user_data.get("name", "Unknown")
        self.entity_id = f"sensor.{ENTITY_PREFIX}_notifiers_{short_id}"

        self._update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        super()._handle_coordinator_update()

    def _update_attrs(self) -> None:
        """Update sensor attributes."""
        user_data = self.coordinator.data["users"].get(self.user_id, {})

        if not user_data:
            # User no longer exists
            self._attr_available = False
            return

        self._attr_available = True
        name = user_data.get("name", "Unknown")
        notifiers = user_data.get("notifiers", [])

        # Set friendly name
        self._attr_name = f"{name} Notifiers"

        # State is JSON list string
        self._attr_native_value = json.dumps(notifiers)

        # Attributes
        self._attr_extra_state_attributes = {
            "notifiers": notifiers,
            "user_id": self.user_id,
            "name": name,
            "role": user_data.get("role", ""),
            "onboard": user_data.get("onboard", False),
            "notify": user_data.get("notify", True),
        }


class OnboardActiveNotifiersAllSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing all active notifiers."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{config_entry.entry_id}_active_notifiers_all"
        self._attr_name = "Active Notifiers (All)"
        self.entity_id = f"sensor.{ENTITY_PREFIX}_active_notifiers_all"
        self._update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        super()._handle_coordinator_update()

    def _update_attrs(self) -> None:
        """Update sensor attributes."""
        active_notifiers = self.coordinator.data.get("active_notifiers_all", [])

        # State is JSON list string
        self._attr_native_value = json.dumps(active_notifiers)

        # Attributes
        self._attr_extra_state_attributes = {
            "notifiers": active_notifiers,
            "count": len(active_notifiers),
        }


class OnboardActiveNotifiersRoleSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing active notifiers for a specific role."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
        role_slug: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.role_slug = role_slug
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{config_entry.entry_id}_active_notifiers_role_{role_slug}"

        # Get role label
        role_label = role_slug
        for role in coordinator.data.get("roles", []):
            if role["slug"] == role_slug:
                role_label = role["label"]
                break

        self._attr_name = f"Active Notifiers (Role: {role_label})"
        self.entity_id = f"sensor.{ENTITY_PREFIX}_active_notifiers_role_{role_slug}"
        self._update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Check if role still exists
        current_role_slugs = {
            role["slug"] for role in self.coordinator.data.get("roles", [])
        }
        if self.role_slug not in current_role_slugs:
            self._attr_available = False
        else:
            self._attr_available = True
            self._update_attrs()

        super()._handle_coordinator_update()

    def _update_attrs(self) -> None:
        """Update sensor attributes."""
        active_by_role = self.coordinator.data.get("active_notifiers_by_role", {})
        active_notifiers = active_by_role.get(self.role_slug, [])

        # State is JSON list string
        self._attr_native_value = json.dumps(active_notifiers)

        # Attributes
        self._attr_extra_state_attributes = {
            "notifiers": active_notifiers,
            "role": self.role_slug,
            "count": len(active_notifiers),
        }
