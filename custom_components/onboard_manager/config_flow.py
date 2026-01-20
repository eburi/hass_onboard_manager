"""Config flow for Onboard Manager integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def parse_roles(roles_input: str) -> list[dict[str, str]]:
    """Parse comma-separated roles and create role objects with slug."""
    roles = []
    seen_slugs = set()

    for role_label in roles_input.split(","):
        role_label = role_label.strip()
        if not role_label:
            continue

        # Create slug: lowercase, replace spaces/hyphens with underscore, remove non-alphanum
        slug = role_label.lower()
        slug = re.sub(r"[\s\-]+", "_", slug)
        slug = re.sub(r"[^a-z0-9_]", "", slug)

        # Ensure unique slug
        original_slug = slug
        counter = 1
        while slug in seen_slugs:
            slug = f"{original_slug}_{counter}"
            counter += 1

        if slug:  # Only add if slug is not empty
            roles.append({"label": role_label, "slug": slug})
            seen_slugs.add(slug)

    return roles


def roles_to_string(roles: list[dict[str, str]]) -> str:
    """Convert roles list to comma-separated string."""
    return ", ".join(role["label"] for role in roles)


class OnboardManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Onboard Manager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            roles_input = user_input.get("roles", "")
            roles = parse_roles(roles_input)

            if not roles:
                errors["roles"] = "no_roles"
            else:
                # Create the config entry
                return self.async_create_entry(
                    title="Onboard Manager",
                    data={"roles": roles},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("roles", default="Crew, Passenger, Guest"): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OnboardManagerOptionsFlow:
        """Get the options flow for this handler."""
        return OnboardManagerOptionsFlow(config_entry)


class OnboardManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Onboard Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            roles_input = user_input.get("roles", "")
            roles = parse_roles(roles_input)

            if not roles:
                errors["roles"] = "no_roles"
            else:
                # Update the config entry data
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={"roles": roles},
                )

                # Trigger coordinator update via the integration
                if DOMAIN in self.hass.data:
                    entry_data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
                    if entry_data and "coordinator" in entry_data:
                        coordinator = entry_data["coordinator"]
                        await coordinator.async_update_roles(roles)

                return self.async_create_entry(title="", data={})

        # Get current roles
        current_roles = self.config_entry.data.get("roles", [])
        current_roles_str = roles_to_string(current_roles)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("roles", default=current_roles_str): str,
                }
            ),
            errors=errors,
        )
