"""Storage management for Onboard Manager."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class OnboardStorage:
    """Handle persistent storage for onboard manager."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {"roles": [], "users": {}}

    async def async_load(self) -> dict[str, Any]:
        """Load data from storage."""
        data = await self._store.async_load()
        if data is None:
            data = {"roles": [], "users": {}}
        self._data = data
        return self._data

    async def async_save(self) -> None:
        """Save data to storage."""
        await self._store.async_save(self._data)

    def get_data(self) -> dict[str, Any]:
        """Get current data."""
        return self._data

    def update_data(self, data: dict[str, Any]) -> None:
        """Update data."""
        self._data = data

    def get_roles(self) -> list[dict[str, str]]:
        """Get configured roles."""
        return self._data.get("roles", [])

    def set_roles(self, roles: list[dict[str, str]]) -> None:
        """Set roles."""
        self._data["roles"] = roles

    def get_users(self) -> dict[str, dict[str, Any]]:
        """Get all user data."""
        return self._data.get("users", {})

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Get a specific user."""
        return self._data.get("users", {}).get(user_id)

    def set_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Set user data."""
        if "users" not in self._data:
            self._data["users"] = {}
        self._data["users"][user_id] = user_data

    def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        if "users" in self._data and user_id in self._data["users"]:
            del self._data["users"][user_id]

    def update_user(self, user_id: str, updates: dict[str, Any]) -> None:
        """Update specific fields of a user."""
        if "users" not in self._data:
            self._data["users"] = {}
        if user_id not in self._data["users"]:
            self._data["users"][user_id] = {}
        self._data["users"][user_id].update(updates)
