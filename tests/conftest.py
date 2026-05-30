"""Pytest configuration for integration tests."""

import pytest
import requests


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


@pytest.fixture(scope="session")
def check_services():
    """Check if required services are running."""
    services = {
        "preprocessing": "http://localhost:8001/api/v1/health",
        "model-base": "http://localhost:8002/api/v1/health",
    }

    missing = []
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                missing.append(name)
        except requests.exceptions.ConnectionError:
            missing.append(name)

    if missing:
        pytest.skip(f"Services not running: {', '.join(missing)}")
