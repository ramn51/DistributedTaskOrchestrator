"""
Integration tests for TitanClient — require a running Titan master on localhost:9090.

Run with:
    pytest -m integration

Skip automatically in CI unless TITAN_INTEGRATION=1 is set.
"""
import os
import uuid
import pytest
from titan_sdk.titan_sdk import TitanClient


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_server():
    if not os.environ.get("TITAN_INTEGRATION"):
        pytest.skip("Set TITAN_INTEGRATION=1 to run integration tests")


@pytest.fixture
def c():
    return TitanClient()


@pytest.fixture
def key():
    """Unique key per test to avoid cross-test pollution."""
    return f"test:{uuid.uuid4().hex}"


class TestStoreRoundtrip:

    def test_put_then_get(self, c, key):
        c.store_put(key, "hello")
        assert c.store_get(key) == "hello"

    def test_overwrite_value(self, c, key):
        c.store_put(key, "first")
        c.store_put(key, "second")
        assert c.store_get(key) == "second"

    def test_get_missing_key_returns_null_or_empty(self, c):
        val = c.store_get(f"test:nonexistent:{uuid.uuid4().hex}")
        assert val in ("", "NULL", None)

    def test_put_unicode_value(self, c, key):
        c.store_put(key, "Ångström — 量子")
        result = c.store_get(key)
        assert "Ångström" in result

    def test_put_long_value(self, c, key):
        long_val = "x" * 4000
        c.store_put(key, long_val)
        assert c.store_get(key) == long_val


class TestSetOperations:

    def test_sadd_new_member_returns_one(self, c, key):
        assert c.store_sadd(key, "member_a") == 1

    def test_sadd_duplicate_returns_zero(self, c, key):
        c.store_sadd(key, "member_a")
        assert c.store_sadd(key, "member_a") == 0

    def test_smembers_returns_added_members(self, c, key):
        c.store_sadd(key, "alpha")
        c.store_sadd(key, "beta")
        members = c.store_smembers(key)
        assert "alpha" in members
        assert "beta" in members

    def test_smembers_empty_set_returns_empty_list(self, c):
        result = c.store_smembers(f"test:empty:{uuid.uuid4().hex}")
        assert result == [] or result == [""]


class TestConnectionErrors:

    def test_wrong_port_returns_connection_error(self):
        import titan_sdk.titan_sdk as m
        original = m.TITAN_PORT
        m.TITAN_PORT = 19999  # nothing listening here
        try:
            c = TitanClient()
            result = c.store_get("any:key")
            assert "ERROR" in result or result == ""
        finally:
            m.TITAN_PORT = original
