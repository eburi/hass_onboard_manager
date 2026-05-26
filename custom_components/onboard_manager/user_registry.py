"""User registry and sync for Onboard Manager."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DEFAULT_NOTIFY, DEFAULT_NOTIFIERS, DEFAULT_ONBOARD

_LOGGER = logging.getLogger(__name__)

MOBILE_APP_DOMAIN = "mobile_app"
MOBILE_APP_DATA_CONFIG_ENTRIES = "config_entries"
MOBILE_APP_DATA_DEVICES = "devices"
MOBILE_APP_DATA_NOTIFY = "notify"


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


def deduplicate_notifiers(notifiers: list[str]) -> list[str]:
    """Deduplicate notifiers while preserving order."""
    deduplicated: list[str] = []
    seen: set[str] = set()

    for notifier in parse_notifiers_input(notifiers):
        if notifier in seen:
            continue
        deduplicated.append(notifier)
        seen.add(notifier)

    return deduplicated


def get_auto_notifiers(user_data: dict[str, Any]) -> list[str]:
    """Return automatically discovered notifiers for a user."""
    return deduplicate_notifiers(user_data.get("auto_notifiers", []))


def get_manual_notifiers(user_data: dict[str, Any]) -> list[str]:
    """Return manually configured notifiers for a user."""
    if "manual_notifiers" in user_data:
        return deduplicate_notifiers(user_data.get("manual_notifiers", []))

    auto_notifiers = set(get_auto_notifiers(user_data))
    return [
        notifier
        for notifier in deduplicate_notifiers(user_data.get("notifiers", []))
        if notifier not in auto_notifiers
    ]


def merge_notifiers(
    manual_notifiers: list[str], auto_notifiers: list[str]
) -> list[str]:
    """Merge manual and automatic notifiers."""
    return deduplicate_notifiers([*manual_notifiers, *auto_notifiers])


def normalize_user_record(user_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize user notifier fields for storage and coordinator state."""
    normalized = user_data.copy()
    manual_notifiers = get_manual_notifiers(normalized)
    auto_notifiers = get_auto_notifiers(normalized)

    normalized["manual_notifiers"] = manual_notifiers
    normalized["auto_notifiers"] = auto_notifiers
    normalized["notifiers"] = merge_notifiers(manual_notifiers, auto_notifiers)

    return normalized


def normalize_users(users: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Normalize all stored users."""
    return {
        user_id: normalize_user_record(user_data)
        for user_id, user_data in users.items()
    }


def get_mobile_app_notify_service(hass: HomeAssistant, webhook_id: str) -> str | None:
    """Return the notify service name for a mobile_app webhook."""
    mobile_app_data = hass.data.get(MOBILE_APP_DOMAIN, {})
    notify_service = mobile_app_data.get(MOBILE_APP_DATA_NOTIFY)
    if notify_service is None:
        return None

    for target_service, target_webhook_id in notify_service.registered_targets.items():
        if target_webhook_id == webhook_id:
            return target_service

    return None


async def get_ha_users(hass: HomeAssistant) -> list[User]:
    """Get all human Home Assistant users."""
    users = await hass.auth.async_get_users()
    # Filter out system users and get only human users
    return [user for user in users if not user.system_generated and user.is_active]


def get_user_device_notifiers(hass: HomeAssistant, user_id: str) -> list[str]:
    """Resolve notify services from a user's person-linked devices."""
    mobile_app_data = hass.data.get(MOBILE_APP_DOMAIN)
    if (
        not mobile_app_data
        or MOBILE_APP_DATA_NOTIFY not in mobile_app_data
        or MOBILE_APP_DATA_DEVICES not in mobile_app_data
    ):
        return []

    entity_registry = er.async_get(hass)

    tracker_device_ids: list[str] = []
    seen_device_ids: set[str] = set()
    for person_state in hass.states.async_all("person"):
        if person_state.attributes.get("user_id") != user_id:
            continue

        for entity_id in person_state.attributes.get("device_trackers", []):
            if (
                not (entry := entity_registry.async_get(entity_id))
                or not entry.device_id
            ):
                continue
            if entry.device_id in seen_device_ids:
                continue
            tracker_device_ids.append(entry.device_id)
            seen_device_ids.add(entry.device_id)

    if not tracker_device_ids:
        return []

    device_to_webhook_id = {
        device.id: webhook_id
        for webhook_id, device in mobile_app_data[MOBILE_APP_DATA_DEVICES].items()
    }

    notifiers: list[str] = []
    for device_id in tracker_device_ids:
        webhook_id = device_to_webhook_id.get(device_id)
        if not webhook_id:
            continue

        if webhook_id not in mobile_app_data.get(MOBILE_APP_DATA_CONFIG_ENTRIES, {}):
            continue

        if service_name := get_mobile_app_notify_service(hass, webhook_id):
            notifiers.append(normalize_notifier(service_name))

    return deduplicate_notifiers(notifiers)


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
            user_data = normalize_user_record(storage_users[user_id])
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
                "manual_notifiers": DEFAULT_NOTIFIERS.copy(),
                "auto_notifiers": [],
            }

        auto_notifiers = get_user_device_notifiers(hass, user_id)
        user_data["auto_notifiers"] = auto_notifiers
        user_data["manual_notifiers"] = get_manual_notifiers(user_data)
        user_data["notifiers"] = merge_notifiers(
            user_data["manual_notifiers"], auto_notifiers
        )

        updated_users[user_id] = user_data

    # Find removed users
    for stored_user_id in storage_users:
        if stored_user_id not in ha_user_ids:
            removed_user_ids.add(stored_user_id)
            _LOGGER.info(
                f"Removing user {storage_users[stored_user_id].get('name', stored_user_id)}"
            )

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
