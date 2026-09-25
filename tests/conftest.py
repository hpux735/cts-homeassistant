"""Shared pytest configuration."""

import pytest


@pytest.fixture(autouse=True)
def enable_custom_component(enable_custom_integrations):
    """Allow Home Assistant to load the local custom integration."""
    return enable_custom_integrations
