"""Coordinator for Onboard Manager."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL_SECONDS
from .storage import OnboardStorage
from .user_registry import (
    compute_active_notifiers,
    compute_active_notifiers_by_role,
    sync_users,
)

_LOGGER = logging.getLogger(__name__)


class OnboardManagerCoordinator(DataUpdateCoordinator):
    """Coordinator to manage onboard manager state."""

    def __init__(
        self,
        hass: HomeAssistant,
        storage: OnboardStorage,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.storage = storage

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from storage and compute aggregates."""
        try:
            # Get current data from storage
            data = self.storage.get_data()
            roles = data.get("roles", [])
            users = data.get("users", {})

            # Sync users with Home Assistant
            updated_users, removed_user_ids = await sync_users(
                self.hass, users, roles
            )

            # Update storage with synced users
            if removed_user_ids or updated_users != users:
                self.storage.update_data({"roles": roles, "users": updated_users})
                await self.storage.async_save()

            # Compute active notifiers
            active_notifiers_all = compute_active_notifiers(updated_users)
            active_notifiers_by_role = compute_active_notifiers_by_role(updated_users)

            # Return coordinated state
            return {
                "roles": roles,
                "users": updated_users,
                "active_notifiers_all": active_notifiers_all,
                "active_notifiers_by_role": active_notifiers_by_role,
                "removed_user_ids": removed_user_ids,
            }

        except Exception as err:
            raise UpdateFailed(f"Error updating onboard manager data: {err}") from err

    async def async_reload_users(self) -> None:
        """Force reload of users."""
        await self.async_refresh()

    async def async_update_user(
        self,
        user_id: str,
        updates: dict[str, Any],
    ) -> None:
        """Update a user's settings and refresh."""
        self.storage.update_user(user_id, updates)
        await self.storage.async_save()
        await self.async_refresh()

    async def async_update_roles(self, roles: list[dict[str, str]]) -> None:
        """Update roles and reassign users if needed."""
        data = self.storage.get_data()
        old_roles = data.get("roles", [])
        users = data.get("users", {})

        # Get valid role slugs
        valid_slugs = {role["slug"] for role in roles}
        default_slug = roles[0]["slug"] if roles else "default"

        # Reassign users with invalid roles
        for user_id, user_data in users.items():
            if user_data.get("role") not in valid_slugs:
                _LOGGER.info(
                    f"Reassigning user {user_data.get('name', user_id)} from "
                    f"{user_data.get('role')} to {default_slug}"
                )
                user_data["role"] = default_slug

        # Update storage
        self.storage.update_data({"roles": roles, "users": users})
        await self.storage.async_save()
        await self.async_refresh()
