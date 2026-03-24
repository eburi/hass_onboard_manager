"""Tests for config_flow module."""

from __future__ import annotations


from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.onboard_manager.config_flow import (
    parse_roles,
    roles_to_string,
)
from custom_components.onboard_manager.const import DOMAIN


def test_parse_roles_basic() -> None:
    """Test basic role parsing."""
    roles = parse_roles("Crew, Passenger, Guest")
    assert len(roles) == 3
    assert roles[0] == {"label": "Crew", "slug": "crew"}
    assert roles[1] == {"label": "Passenger", "slug": "passenger"}
    assert roles[2] == {"label": "Guest", "slug": "guest"}


def test_parse_roles_slug_normalization() -> None:
    """Test that special characters are stripped from slugs."""
    roles = parse_roles("First Mate, 2nd-Officer")
    assert roles[0]["slug"] == "first_mate"
    assert roles[1]["slug"] == "2nd_officer"


def test_parse_roles_empty() -> None:
    """Test parsing empty string returns empty list."""
    assert parse_roles("") == []
    assert parse_roles("   ") == []


def test_parse_roles_duplicates() -> None:
    """Test that duplicate slugs get numbered suffixes."""
    roles = parse_roles("Crew, crew")
    assert len(roles) == 2
    assert roles[0]["slug"] == "crew"
    assert roles[1]["slug"] == "crew_1"


def test_roles_to_string() -> None:
    """Test converting roles list to string."""
    roles = [
        {"label": "Crew", "slug": "crew"},
        {"label": "Passenger", "slug": "passenger"},
    ]
    assert roles_to_string(roles) == "Crew, Passenger"


def test_roles_to_string_empty() -> None:
    """Test converting empty roles list to string."""
    assert roles_to_string([]) == ""


async def test_config_flow_user_step(hass: HomeAssistant) -> None:
    """Test the user config flow step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_config_flow_user_step_creates_entry(hass: HomeAssistant) -> None:
    """Test that submitting the user step creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"roles": "Crew, Passenger"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Onboard Manager"
    assert len(result["data"]["roles"]) == 2


async def test_config_flow_user_step_no_roles(hass: HomeAssistant) -> None:
    """Test that empty roles shows an error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"roles": ""},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"roles": "no_roles"}
