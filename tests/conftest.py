"""Fixtures for Onboard Manager tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.onboard_manager.storage import OnboardStorage


@pytest.fixture
def mock_roles() -> list[dict[str, str]]:
    """Return a list of test roles."""
    return [
        {"label": "Crew", "slug": "crew"},
        {"label": "Passenger", "slug": "passenger"},
        {"label": "Guest", "slug": "guest"},
    ]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture
def mock_users() -> dict[str, dict[str, Any]]:
    """Return a dict of test users."""
    return {
        "user_aaa": {
            "user_id": "user_aaa",
            "name": "Alice",
            "onboard": True,
            "notify": True,
            "role": "crew",
            "notifiers": ["notify.mobile_app_alice"],
        },
        "user_bbb": {
            "user_id": "user_bbb",
            "name": "Bob",
            "onboard": False,
            "notify": True,
            "role": "passenger",
            "notifiers": ["notify.mobile_app_bob"],
        },
        "user_ccc": {
            "user_id": "user_ccc",
            "name": "Charlie",
            "onboard": True,
            "notify": False,
            "role": "crew",
            "notifiers": ["notify.mobile_app_charlie"],
        },
    }


@pytest.fixture
def mock_storage_data(
    mock_roles: list[dict[str, str]],
    mock_users: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return test storage data."""
    return {
        "roles": mock_roles,
        "users": mock_users,
    }


@pytest.fixture
def mock_storage(
    hass: HomeAssistant, mock_storage_data: dict[str, Any]
) -> OnboardStorage:
    """Return a mocked OnboardStorage."""
    storage = OnboardStorage(hass)
    storage._data = mock_storage_data
    storage.async_save = AsyncMock()
    storage.async_load = AsyncMock(return_value=mock_storage_data)
    return storage
