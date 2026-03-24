"""Tests for user_registry module."""

from __future__ import annotations

from typing import Any


from custom_components.onboard_manager.user_registry import (
    compute_active_notifiers,
    compute_active_notifiers_by_role,
    get_short_id,
    normalize_notifier,
    parse_notifiers_input,
)


def test_get_short_id() -> None:
    """Test short ID extraction."""
    assert get_short_id("abcdefghijklmnop") == "abcdefgh"
    assert get_short_id("12345678") == "12345678"


def test_normalize_notifier() -> None:
    """Test notifier normalization."""
    assert normalize_notifier("mobile_app_alice") == "notify.mobile_app_alice"
    assert normalize_notifier("notify.mobile_app_alice") == "notify.mobile_app_alice"
    assert normalize_notifier("  mobile_app_bob  ") == "notify.mobile_app_bob"
    assert normalize_notifier("  notify.foo  ") == "notify.foo"


def test_parse_notifiers_input_string() -> None:
    """Test parsing comma-separated string input."""
    result = parse_notifiers_input("mobile_app_alice, notify.mobile_app_bob")
    assert result == ["notify.mobile_app_alice", "notify.mobile_app_bob"]


def test_parse_notifiers_input_list() -> None:
    """Test parsing list input."""
    result = parse_notifiers_input(["mobile_app_alice", "notify.mobile_app_bob"])
    assert result == ["notify.mobile_app_alice", "notify.mobile_app_bob"]


def test_parse_notifiers_input_empty_string() -> None:
    """Test parsing empty string."""
    assert parse_notifiers_input("") == []


def test_parse_notifiers_input_invalid_type() -> None:
    """Test parsing invalid type returns empty list."""
    assert parse_notifiers_input(123) == []


def test_compute_active_notifiers(
    mock_users: dict[str, dict[str, Any]],
) -> None:
    """Test computing active notifiers for all users.

    Alice: onboard=True, notify=True -> included
    Bob: onboard=False, notify=True -> excluded (not onboard)
    Charlie: onboard=True, notify=False -> excluded (notify off)
    """
    result = compute_active_notifiers(mock_users)
    assert result == ["notify.mobile_app_alice"]


def test_compute_active_notifiers_empty() -> None:
    """Test computing active notifiers with no users."""
    assert compute_active_notifiers({}) == []


def test_compute_active_notifiers_deduplication() -> None:
    """Test that duplicate notifiers are deduplicated."""
    users = {
        "u1": {
            "onboard": True,
            "notify": True,
            "notifiers": ["notify.shared"],
        },
        "u2": {
            "onboard": True,
            "notify": True,
            "notifiers": ["notify.shared"],
        },
    }
    result = compute_active_notifiers(users)
    assert result == ["notify.shared"]


def test_compute_active_notifiers_by_role(
    mock_users: dict[str, dict[str, Any]],
) -> None:
    """Test computing active notifiers grouped by role.

    Only Alice (crew, onboard, notify) qualifies.
    """
    result = compute_active_notifiers_by_role(mock_users)
    assert result == {"crew": ["notify.mobile_app_alice"]}


def test_compute_active_notifiers_by_role_empty() -> None:
    """Test computing active notifiers by role with no users."""
    assert compute_active_notifiers_by_role({}) == {}
