"""Tests for netbox_healthcheck_plugin package."""

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestHealthCheckPlugin:
    """Test suite for NetBox HealthCheck Plugin."""

    def test_plugin_config(self) -> None:
        """Test that plugin config is properly defined."""
        from netbox_healthcheck_plugin import HealthCheckConfig

        assert HealthCheckConfig.name == 'netbox_healthcheck_plugin'
        assert HealthCheckConfig.version == '0.3.0'
        assert HealthCheckConfig.min_version == '4.5.0'

    def test_healthcheck_endpoint_exists(self) -> None:
        """Test that the healthcheck URL is accessible."""
        client = Client()
        url = reverse('plugins:netbox_healthcheck_plugin:healthcheck_list')
        response = client.get(url)

        # Should return 200 or redirect (depending on NetBox setup)
        assert response.status_code in [200, 302]
