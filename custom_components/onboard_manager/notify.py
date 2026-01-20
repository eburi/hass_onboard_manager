"""Notify platform for Onboard Manager."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TARGET,
    ATTR_TITLE,
    NotifyEntity,
)
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
    """Set up Onboard Manager notify entities."""
    coordinator: OnboardManagerCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities: list[NotifyEntity] = []

    # Create per-user notify groups
    for user_id in coordinator.data["users"]:
        entities.append(UserNotifyEntity(coordinator, config_entry, user_id))

    # Create "all active" notify group
    entities.append(AllActiveNotifyEntity(coordinator, config_entry))

    # Create per-role notify groups
    for role in coordinator.data["roles"]:
        entities.append(RoleNotifyEntity(coordinator, config_entry, role["slug"]))

    async_add_entities(entities)

    # Register platform update callback to handle user/role additions/removals
    @callback
    def async_add_remove_entities() -> None:
        """Add or remove entities based on coordinator data."""
        current_users = coordinator.data.get("users", {})
        current_roles = coordinator.data.get("roles", [])

        # Get existing entity user IDs
        existing_user_ids = {
            entity.user_id
            for entity in entities
            if isinstance(entity, UserNotifyEntity)
        }

        # Get existing role slugs
        existing_role_slugs = {
            entity.role_slug
            for entity in entities
            if isinstance(entity, RoleNotifyEntity)
        }

        new_entities = []

        # Add notify entities for new users
        for user_id in current_users:
            if user_id not in existing_user_ids:
                new_entities.append(
                    UserNotifyEntity(coordinator, config_entry, user_id)
                )

        # Add notify entities for new roles
        current_role_slugs = {role["slug"] for role in current_roles}
        for role_slug in current_role_slugs:
            if role_slug not in existing_role_slugs:
                new_entities.append(
                    RoleNotifyEntity(coordinator, config_entry, role_slug)
                )

        if new_entities:
            async_add_entities(new_entities)
            entities.extend(new_entities)

    # Listen for coordinator updates
    config_entry.async_on_unload(
        coordinator.async_add_listener(async_add_remove_entities)
    )


class UserNotifyEntity(CoordinatorEntity, NotifyEntity):
    """Notify entity for a specific user."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
        user_id: str,
    ) -> None:
        """Initialize the notify entity."""
        super().__init__(coordinator)
        self.user_id = user_id
        self._attr_has_entity_name = False

        short_id = get_short_id(user_id)
        self._attr_unique_id = f"{config_entry.entry_id}_{user_id}_notify_group"

        # Set entity_id suggestion
        self.entity_id = f"notify.{ENTITY_PREFIX}_user_{short_id}"

        self._update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        super()._handle_coordinator_update()

    def _update_attrs(self) -> None:
        """Update entity attributes."""
        user_data = self.coordinator.data["users"].get(self.user_id, {})

        if not user_data:
            # User no longer exists
            self._attr_available = False
            return

        name = user_data.get("name", "Unknown")

        # Respect the notify flag for availability
        # User groups ignore onboard flag (per spec)
        self._attr_available = user_data.get("notify", True)
        self._attr_name = f"Onboard Manager: {name}"

    async def async_send_message(self, message: str, title: str | None = None, **kwargs: Any) -> None:
        """Send a message to all user's notifiers."""
        user_data = self.coordinator.data["users"].get(self.user_id, {})

        if not user_data:
            _LOGGER.warning(f"User {self.user_id} not found")
            return

        # Check if notify is enabled
        if not user_data.get("notify", True):
            _LOGGER.debug(f"Notifications disabled for user {user_data.get('name', self.user_id)}")
            return

        notifiers = user_data.get("notifiers", [])
        if not notifiers:
            _LOGGER.debug(f"No notifiers configured for user {user_data.get('name', self.user_id)}")
            return

        # Build service data
        service_data = {ATTR_MESSAGE: message}
        if title:
            service_data[ATTR_TITLE] = title
        if ATTR_DATA in kwargs:
            service_data[ATTR_DATA] = kwargs[ATTR_DATA]
        if ATTR_TARGET in kwargs:
            service_data[ATTR_TARGET] = kwargs[ATTR_TARGET]

        # Send to all notifiers (deduplicated)
        seen = set()
        for notifier in notifiers:
            if notifier in seen:
                continue
            seen.add(notifier)

            # Parse notifier service name
            if notifier.startswith("notify."):
                service_name = notifier[7:]  # Remove "notify." prefix
            else:
                service_name = notifier

            try:
                await self.hass.services.async_call(
                    "notify",
                    service_name,
                    service_data,
                    blocking=False,
                )
                _LOGGER.debug(f"Sent notification to {notifier}")
            except Exception as err:
                _LOGGER.error(f"Failed to send notification to {notifier}: {err}")


class AllActiveNotifyEntity(CoordinatorEntity, NotifyEntity):
    """Notify entity for all active users."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the notify entity."""
        super().__init__(coordinator)
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{config_entry.entry_id}_notify_all"
        self._attr_name = "Onboard Manager: All Active"
        self.entity_id = f"notify.{ENTITY_PREFIX}_all"

    async def async_send_message(self, message: str, title: str | None = None, **kwargs: Any) -> None:
        """Send a message to all active users' notifiers."""
        notifiers = self.coordinator.data.get("active_notifiers_all", [])

        if not notifiers:
            _LOGGER.debug("No active notifiers for all group")
            return

        # Build service data
        service_data = {ATTR_MESSAGE: message}
        if title:
            service_data[ATTR_TITLE] = title
        if ATTR_DATA in kwargs:
            service_data[ATTR_DATA] = kwargs[ATTR_DATA]
        if ATTR_TARGET in kwargs:
            service_data[ATTR_TARGET] = kwargs[ATTR_TARGET]

        # Send to all notifiers (already deduplicated in coordinator)
        for notifier in notifiers:
            # Parse notifier service name
            if notifier.startswith("notify."):
                service_name = notifier[7:]  # Remove "notify." prefix
            else:
                service_name = notifier

            try:
                await self.hass.services.async_call(
                    "notify",
                    service_name,
                    service_data,
                    blocking=False,
                )
                _LOGGER.debug(f"Sent notification to {notifier}")
            except Exception as err:
                _LOGGER.error(f"Failed to send notification to {notifier}: {err}")


class RoleNotifyEntity(CoordinatorEntity, NotifyEntity):
    """Notify entity for a specific role."""

    def __init__(
        self,
        coordinator: OnboardManagerCoordinator,
        config_entry: ConfigEntry,
        role_slug: str,
    ) -> None:
        """Initialize the notify entity."""
        super().__init__(coordinator)
        self.role_slug = role_slug
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{config_entry.entry_id}_notify_role_{role_slug}"

        # Get role label
        role_label = role_slug
        for role in coordinator.data.get("roles", []):
            if role["slug"] == role_slug:
                role_label = role["label"]
                break

        self._attr_name = f"Onboard Manager: Role {role_label}"
        self.entity_id = f"notify.{ENTITY_PREFIX}_role_{role_slug}"

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

        super()._handle_coordinator_update()

    async def async_send_message(self, message: str, title: str | None = None, **kwargs: Any) -> None:
        """Send a message to all active users in this role."""
        active_by_role = self.coordinator.data.get("active_notifiers_by_role", {})
        notifiers = active_by_role.get(self.role_slug, [])

        if not notifiers:
            _LOGGER.debug(f"No active notifiers for role {self.role_slug}")
            return

        # Build service data
        service_data = {ATTR_MESSAGE: message}
        if title:
            service_data[ATTR_TITLE] = title
        if ATTR_DATA in kwargs:
            service_data[ATTR_DATA] = kwargs[ATTR_DATA]
        if ATTR_TARGET in kwargs:
            service_data[ATTR_TARGET] = kwargs[ATTR_TARGET]

        # Send to all notifiers (already deduplicated in coordinator)
        for notifier in notifiers:
            # Parse notifier service name
            if notifier.startswith("notify."):
                service_name = notifier[7:]  # Remove "notify." prefix
            else:
                service_name = notifier

            try:
                await self.hass.services.async_call(
                    "notify",
                    service_name,
                    service_data,
                    blocking=False,
                )
                _LOGGER.debug(f"Sent notification to {notifier}")
            except Exception as err:
                _LOGGER.error(f"Failed to send notification to {notifier}: {err}")
