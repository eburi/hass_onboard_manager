"""Services for Onboard Manager."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    NOTIFIER_MODE_ADD,
    NOTIFIER_MODE_REMOVE,
    NOTIFIER_MODE_REPLACE,
    SERVICE_EXPORT_STATE,
    SERVICE_RELOAD_USERS,
    SERVICE_SET_USER,
    SERVICE_SET_USER_NOTIFIERS,
)
from .coordinator import OnboardManagerCoordinator
from .user_registry import parse_notifiers_input, resolve_user_id

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_SET_USER_SCHEMA = vol.Schema(
    {
        vol.Optional("user_id"): cv.string,
        vol.Optional("username"): cv.string,
        vol.Optional("onboard"): cv.boolean,
        vol.Optional("notify"): cv.boolean,
        vol.Optional("role"): cv.string,
    }
)

SERVICE_SET_USER_NOTIFIERS_SCHEMA = vol.Schema(
    {
        vol.Optional("user_id"): cv.string,
        vol.Optional("username"): cv.string,
        vol.Required("notifiers"): vol.Any(cv.string, [cv.string]),
        vol.Optional("mode", default=NOTIFIER_MODE_REPLACE): vol.In(
            [NOTIFIER_MODE_REPLACE, NOTIFIER_MODE_ADD, NOTIFIER_MODE_REMOVE]
        ),
    }
)


def register_services(hass: HomeAssistant, coordinator: OnboardManagerCoordinator) -> None:
    """Register services for onboard manager."""

    async def handle_set_user(call: ServiceCall) -> None:
        """Handle set_user service call."""
        user_id = await resolve_user_id(
            hass,
            call.data.get("user_id"),
            call.data.get("username"),
        )

        if not user_id:
            _LOGGER.error("Could not resolve user_id or username")
            return

        # Check if user exists in coordinator data
        users = coordinator.data.get("users", {})
        if user_id not in users:
            _LOGGER.error(f"User {user_id} not found in onboard manager")
            return

        # Build updates
        updates = {}

        if "onboard" in call.data:
            updates["onboard"] = call.data["onboard"]

        if "notify" in call.data:
            updates["notify"] = call.data["notify"]

        if "role" in call.data:
            role_input = call.data["role"]
            # Validate role exists (by slug or label)
            roles = coordinator.data.get("roles", [])
            role_slug = None

            # Try to match by slug first
            for role in roles:
                if role["slug"] == role_input.lower():
                    role_slug = role["slug"]
                    break

            # Try to match by label
            if not role_slug:
                for role in roles:
                    if role["label"].lower() == role_input.lower():
                        role_slug = role["slug"]
                        break

            if role_slug:
                updates["role"] = role_slug
            else:
                _LOGGER.error(f"Invalid role: {role_input}")
                return

        if updates:
            await coordinator.async_update_user(user_id, updates)
            _LOGGER.info(f"Updated user {user_id}: {updates}")

    async def handle_set_user_notifiers(call: ServiceCall) -> None:
        """Handle set_user_notifiers service call."""
        user_id = await resolve_user_id(
            hass,
            call.data.get("user_id"),
            call.data.get("username"),
        )

        if not user_id:
            _LOGGER.error("Could not resolve user_id or username")
            return

        # Check if user exists in coordinator data
        users = coordinator.data.get("users", {})
        if user_id not in users:
            _LOGGER.error(f"User {user_id} not found in onboard manager")
            return

        user_data = users[user_id]
        current_notifiers = user_data.get("notifiers", [])

        # Parse new notifiers
        new_notifiers = parse_notifiers_input(call.data["notifiers"])
        mode = call.data.get("mode", NOTIFIER_MODE_REPLACE)

        # Apply mode
        if mode == NOTIFIER_MODE_REPLACE:
            updated_notifiers = new_notifiers
        elif mode == NOTIFIER_MODE_ADD:
            # Add new notifiers that aren't already present
            updated_notifiers = current_notifiers.copy()
            for notifier in new_notifiers:
                if notifier not in updated_notifiers:
                    updated_notifiers.append(notifier)
        elif mode == NOTIFIER_MODE_REMOVE:
            # Remove specified notifiers
            updated_notifiers = [
                n for n in current_notifiers if n not in new_notifiers
            ]
        else:
            _LOGGER.error(f"Invalid mode: {mode}")
            return

        await coordinator.async_update_user(user_id, {"notifiers": updated_notifiers})
        _LOGGER.info(f"Updated notifiers for user {user_id}: {updated_notifiers}")

    async def handle_reload_users(call: ServiceCall) -> None:
        """Handle reload_users service call."""
        await coordinator.async_reload_users()
        _LOGGER.info("Reloaded users")

    async def handle_export_state(call: ServiceCall) -> ServiceResponse:
        """Handle export_state service call."""
        data = coordinator.data
        return {
            "roles": data.get("roles", []),
            "users": data.get("users", {}),
            "active_notifiers_all": data.get("active_notifiers_all", []),
            "active_notifiers_by_role": data.get("active_notifiers_by_role", {}),
        }

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_USER,
        handle_set_user,
        schema=SERVICE_SET_USER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_USER_NOTIFIERS,
        handle_set_user_notifiers,
        schema=SERVICE_SET_USER_NOTIFIERS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD_USERS,
        handle_reload_users,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_STATE,
        handle_export_state,
        supports_response=SupportsResponse.ONLY,
    )


def unregister_services(hass: HomeAssistant) -> None:
    """Unregister services for onboard manager."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_USER)
    hass.services.async_remove(DOMAIN, SERVICE_SET_USER_NOTIFIERS)
    hass.services.async_remove(DOMAIN, SERVICE_RELOAD_USERS)
    hass.services.async_remove(DOMAIN, SERVICE_EXPORT_STATE)
