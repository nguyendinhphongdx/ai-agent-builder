"""Unit tests for the SSRF guard. Pure — uses ipaddress / socket directly."""
from __future__ import annotations

import pytest

from app.tools.url_guard import _is_blocked_ip, assert_safe_url


def test_blocks_private_ipv4():
    assert _is_blocked_ip("10.0.0.5") is True
    assert _is_blocked_ip("192.168.1.1") is True
    assert _is_blocked_ip("172.16.0.1") is True


def test_blocks_loopback():
    assert _is_blocked_ip("127.0.0.1") is True
    assert _is_blocked_ip("::1") is True


def test_blocks_link_local():
    """169.254.0.0/16 — includes the AWS metadata endpoint 169.254.169.254."""
    assert _is_blocked_ip("169.254.169.254") is True


def test_allows_public_ipv4():
    assert _is_blocked_ip("8.8.8.8") is False
    assert _is_blocked_ip("1.1.1.1") is False


def test_assert_safe_url_rejects_file_scheme():
    with pytest.raises(ValueError, match="scheme"):
        assert_safe_url("file:///etc/passwd")


def test_assert_safe_url_rejects_empty_host():
    with pytest.raises(ValueError, match="hostname"):
        assert_safe_url("http:///path")


def test_assert_safe_url_rejects_metadata_host():
    """The cloud metadata host doesn't resolve to a private IP via DNS,
    so we maintain a name-level blocklist too."""
    with pytest.raises(ValueError, match="not allowed"):
        assert_safe_url("http://metadata.google.internal/foo")
