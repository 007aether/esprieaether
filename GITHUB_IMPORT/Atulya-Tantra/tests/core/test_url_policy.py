"""Les URL de confiance refusent les ports invalides et les séparateurs vides."""
from __future__ import annotations

import pytest

from atulya.mcp_connections import _validate_url
from atulya.settings import Settings

BASE_SETTINGS = dict(
    assistant_name="Atulya", host="127.0.0.1", port=8501,
    data_dir="data", models_dir="models",
    model_provider="", model_name="", model_base_url="", model_api_key="",
)

BAD_ENDPOINT_PORTS = [
    "https://example.org:99999/mcp",
    "https://example.org:0/mcp",
    "https://example.org:abc/mcp",
    "http://127.0.0.1:/mcp",
]


@pytest.mark.parametrize("bad", BAD_ENDPOINT_PORTS)
def test_mcp_rejects_invalid_ports(bad):
    with pytest.raises(ValueError):
        _validate_url(bad)


@pytest.mark.parametrize("bad", [
    "http://127.0.0.1:3001/mcp?",
    "http://127.0.0.1:3001/mcp#",
    "https://example.org/mcp?",
])
def test_mcp_rejects_empty_query_or_fragment_separator(bad):
    with pytest.raises(ValueError):
        _validate_url(bad)


@pytest.mark.parametrize("good", [
    "http://127.0.0.1:3001/mcp",
    "http://[::1]:3001/mcp",
    "https://example.org/mcp",
    "https://example.org:443/mcp",
])
def test_mcp_keeps_valid_endpoints(good):
    _validate_url(good)


def test_mcp_still_rejects_localhost_and_credentials():
    for bad in ("http://localhost:3001/mcp", "http://@127.0.0.1:3001/mcp"):
        with pytest.raises(ValueError):
            _validate_url(bad)


@pytest.mark.parametrize("bad", BAD_ENDPOINT_PORTS)
def test_landing_rejects_invalid_ports(bad):
    with pytest.raises(ValueError):
        Settings(**BASE_SETTINGS, landing_url=bad)


@pytest.mark.parametrize("bad", BAD_ENDPOINT_PORTS)
def test_public_origin_rejects_invalid_ports(monkeypatch, bad):
    monkeypatch.setenv("ATULYA_PUBLIC_ORIGIN", bad)
    with pytest.raises(ValueError):
        Settings.from_environment()
