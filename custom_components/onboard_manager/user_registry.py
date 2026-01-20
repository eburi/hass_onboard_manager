"""User registry and sync for Onboard Manager."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant

from .const import DEFAULT_NOTIFY, DEFAULT_NOTIFIERS, DEFAULT_ONBOARD

_LOGGER = logging.getLogger(__name__)


def get_short_id(user_id: str) -> str:
    """Get a short identifier from user_id (first 8 chars)."""
    return user_id[:8]


def normalize_notifier(notifier: str) -> str:
    """Normalize a notifier service name to include notify. prefix."""
    notifier = notifier.strip()
    if not notifier.startswith("notify."):
        return f"notify.{notifier}"
    return notifier


def parse_notifiers_input(notifiers: Any) -> list[str]:
    """Parse notifiers input (list or comma-separated string)."""
    if isinstance(notifiers, str):
        # Comma-separated string
        notifier_list = [n.strip() for n in notifiers.split(",") if n.strip()]
    elif isinstance(notifiers, list):
        # Already a list
        notifier_list = [str(n).strip() for n in notifiers if str(n).strip()]
    else:
        return []

    # Normalize all notifiers
    return [normalize_notifier(n) for n in notifier_list]


async def get_ha_users(hass: HomeAssistant) -> list[User]:
    """Get all human Home Assistant users."""
    users = await hass.auth.async_get_users()
    # Filter out system users and get only human users
    return [user for user in users if not user.system_generated and user.is_active]


async def sync_users(
    hass: HomeAssistant,
    storage_users: dict[str, dict[str, Any]],
    roles: list[dict[str, str]],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    """
    Sync Home Assistant users with storage.

    Returns:
        Tuple of (updated_users_dict, set_of_removed_user_ids)
    """
    ha_users = await get_ha_users(hass)
    ha_user_ids = {user.id for user in ha_users}

    # Default role slug (first role)
    default_role = roles[0]["slug"] if roles else "default"

    updated_users: dict[str, dict[str, Any]] = {}
    removed_user_ids: set[str] = set()

    # Process existing HA users
    for user in ha_users:
        user_id = user.id
        user_name = user.name or "Unknown"

        if user_id in storage_users:
            # Existing user - update name if changed
            user_data = storage_users[user_id].copy()
            user_data["name"] = user_name
        else:
            # New user - create default record
            _LOGGER.info(f"Creating new user record for {user_name} ({user_id})")
            user_data = {
                "user_id": user_id,
                "name": user_name,
                "onboard": DEFAULT_ONBOARD,
                "notify": DEFAULT_NOTIFY,
                "role": default_role,
                "notifiers": DEFAULT_NOTIFIERS.copy(),
            }

        updated_users[user_id] = user_data

    # Find removed users
    for stored_user_id in storage_users:
        if stored_user_id not in ha_user_ids:
            removed_user_ids.add(stored_user_id)
            _LOGGER.info(f"Removing user {storage_users[stored_user_id].get('name', stored_user_id)}")

    return updated_users, removed_user_ids


def compute_active_notifiers(users: dict[str, dict[str, Any]]) -> list[str]:
    """
    Compute list of active notifiers from all users.

    Active user = onboard == True AND notify == True
    """
    notifiers_set = []
    seen = set()

    for user_data in users.values():
        if user_data.get("onboard", False) and user_data.get("notify", True):
            for notifier in user_data.get("notifiers", []):
                if notifier not in seen:
                    notifiers_set.append(notifier)
                    seen.add(notifier)

    return notifiers_set


def compute_active_notifiers_by_role(
    users: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    """
    Compute active notifiers grouped by role.

    Active user = onboard == True AND notify == True
    """
    by_role: dict[str, list[str]] = {}

    for user_data in users.values():
        if user_data.get("onboard", False) and user_data.get("notify", True):
            role = user_data.get("role", "")
            if role:
                if role not in by_role:
                    by_role[role] = []

                for notifier in user_data.get("notifiers", []):
                    if notifier not in by_role[role]:
                        by_role[role].append(notifier)

    return by_role


async def resolve_user_id(
    hass: HomeAssistant, user_id: str | None = None, username: str | None = None
) -> str | None:
    """Resolve user_id from either user_id or username."""
    if user_id:
        return user_id

    if username:
        users = await hass.auth.async_get_users()
        for user in users:
            if user.name and user.name.lower() == username.lower():
                return user.id

    return None
