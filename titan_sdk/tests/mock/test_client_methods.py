"""
Mock-based tests for TitanClient higher-level methods.

_send_request is patched to return canned responses so no server is needed.
Tests verify that methods build correct payloads and call the right operations.
"""
import pytest
from titan_sdk.titan_sdk import TitanClient, OP_KV_SET, OP_KV_GET, OP_KV_SADD, OP_KV_SMEMBERS, OP_UPLOAD_ASSET, OP_DEPLOY_SCRIPT


@pytest.fixture
def mock_send(monkeypatch):
    """
    Patches _send_request to record calls and return a configurable response.
    Returns a helper object with .calls list and .set_response(str) method.
    """
    class MockSend:
        def __init__(self):
            self.calls = []
            self._response = "OK"

        def set_response(self, r):
            self._response = r

        def __call__(self, op, payload):
            self.calls.append((op, payload))
            return self._response

    m = MockSend()
    monkeypatch.setattr(TitanClient, "_send_request", lambda self, op, payload: m(op, payload))
    return m


# ---------------------------------------------------------------------------
# TitanStore — store_put / store_get
# ---------------------------------------------------------------------------

class TestStoreOperations:

    def test_store_put_uses_kv_set_opcode(self, client, mock_send):
        client.store_put("my:key", "hello")
        assert mock_send.calls[0][0] == OP_KV_SET

    def test_store_put_payload_format(self, client, mock_send):
        client.store_put("my:key", "hello")
        assert mock_send.calls[0][1] == "my:key|hello"

    def test_store_get_uses_kv_get_opcode(self, client, mock_send):
        client.store_get("my:key")
        assert mock_send.calls[0][0] == OP_KV_GET

    def test_store_get_sends_key(self, client, mock_send):
        client.store_get("my:key")
        assert mock_send.calls[0][1] == "my:key"

    def test_store_get_returns_response(self, client, mock_send):
        mock_send.set_response("stored_value")
        assert client.store_get("k") == "stored_value"

    def test_store_sadd_uses_kv_sadd_opcode(self, client, mock_send):
        mock_send.set_response("1")
        client.store_sadd("myset", "member1")
        assert mock_send.calls[0][0] == OP_KV_SADD

    def test_store_sadd_payload_format(self, client, mock_send):
        mock_send.set_response("1")
        client.store_sadd("myset", "member1")
        assert mock_send.calls[0][1] == "myset|member1"

    def test_store_sadd_returns_int(self, client, mock_send):
        mock_send.set_response("1")
        result = client.store_sadd("s", "m")
        assert result == 1
        assert isinstance(result, int)

    def test_store_sadd_returns_zero_for_duplicate(self, client, mock_send):
        mock_send.set_response("0")
        assert client.store_sadd("s", "m") == 0

    def test_store_smembers_uses_correct_opcode(self, client, mock_send):
        mock_send.set_response("a,b,c")
        client.store_smembers("myset")
        assert mock_send.calls[0][0] == OP_KV_SMEMBERS

    def test_store_smembers_returns_list(self, client, mock_send):
        mock_send.set_response("a,b,c")
        result = client.store_smembers("myset")
        assert result == ["a", "b", "c"]

    def test_store_smembers_empty_returns_empty_list(self, client, mock_send):
        mock_send.set_response("")
        assert client.store_smembers("myset") == []


# ---------------------------------------------------------------------------
# File transfer — upload_file
# ---------------------------------------------------------------------------

class TestUploadFile:

    def test_upload_uses_upload_asset_opcode(self, client, mock_send, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("content")
        mock_send.set_response("UPLOAD_SUCCESS")
        client.upload_file(str(f))
        assert mock_send.calls[0][0] == OP_UPLOAD_ASSET

    def test_upload_payload_starts_with_basename(self, client, mock_send, tmp_path):
        f = tmp_path / "myfile.txt"
        f.write_text("hi")
        mock_send.set_response("UPLOAD_SUCCESS")
        client.upload_file(str(f))
        payload = mock_send.calls[0][1]
        assert payload.startswith("myfile.txt|")

    def test_upload_missing_file_returns_error(self, client, mock_send):
        result = client.upload_file("/no/such/file.txt")
        assert result.startswith("ERROR")
        assert len(mock_send.calls) == 0   # should not reach _send_request


# ---------------------------------------------------------------------------
# Artifact workflow — publish_artifact / get_artifact
# ---------------------------------------------------------------------------

class TestPublishArtifact:

    def test_returns_true_on_success(self, client, mock_send, tmp_path):
        f = tmp_path / "report.md"
        f.write_text("report content")
        mock_send.set_response("UPLOAD_SUCCESS")
        assert client.publish_artifact("run:1:report", str(f)) is True

    def test_upload_called(self, client, mock_send, tmp_path):
        f = tmp_path / "report.md"
        f.write_text("x")
        mock_send.set_response("UPLOAD_SUCCESS")
        client.publish_artifact("run:1:report", str(f))
        opcodes = [op for op, _ in mock_send.calls]
        assert OP_UPLOAD_ASSET in opcodes

    def test_store_put_called_with_key_and_basename(self, client, mock_send, tmp_path):
        f = tmp_path / "report.md"
        f.write_text("x")
        mock_send.set_response("UPLOAD_SUCCESS")
        client.publish_artifact("run:1:report", str(f))
        kv_calls = [(op, p) for op, p in mock_send.calls if op == OP_KV_SET]
        assert any("run:1:report|report.md" == p for _, p in kv_calls)

    def test_returns_false_on_upload_failure(self, client, mock_send, tmp_path):
        f = tmp_path / "report.md"
        f.write_text("x")
        mock_send.set_response("ERROR: disk full")
        assert client.publish_artifact("run:1:report", str(f)) is False

    def test_store_put_not_called_on_upload_failure(self, client, mock_send, tmp_path):
        f = tmp_path / "report.md"
        f.write_text("x")
        mock_send.set_response("ERROR: disk full")
        client.publish_artifact("run:1:report", str(f))
        kv_calls = [op for op, _ in mock_send.calls if op == OP_KV_SET]
        assert len(kv_calls) == 0


class TestGetArtifact:

    def test_returns_false_for_null_key(self, client, mock_send):
        mock_send.set_response("NULL")
        assert client.get_artifact("missing:key") is False

    def test_returns_false_for_cleared_key(self, client, mock_send):
        mock_send.set_response("CLEARED")
        assert client.get_artifact("missing:key") is False

    def test_returns_false_for_empty_key(self, client, mock_send):
        mock_send.set_response("")
        assert client.get_artifact("missing:key") is False

    def test_fetches_by_registered_filename(self, client, mock_send, tmp_path):
        """
        First call: store_get returns the basename.
        Second call: fetch_artifact (OP_FETCH_ASSET = 0x54) returns b64 data.
        """
        import base64
        content = base64.b64encode(b"file content").decode()

        call_count = [0]
        def side_effect(op, payload):
            call_count[0] += 1
            if call_count[0] == 1:
                return "report.md"      # store_get returns basename
            return content              # fetch_artifact returns b64

        monkeypatch_obj = mock_send  # already patched; override with custom logic
        import titan_sdk.titan_sdk as sdk_module
        original = TitanClient._send_request
        TitanClient._send_request = lambda self, op, p: side_effect(op, p)
        try:
            save = str(tmp_path / "out.md")
            result = client.get_artifact("run:1:report", save_path=save)
            assert result is True
            assert (tmp_path / "out.md").read_bytes() == b"file content"
        finally:
            TitanClient._send_request = original


# ---------------------------------------------------------------------------
# deploy_script
# ---------------------------------------------------------------------------

class TestDeployScript:

    def test_uses_deploy_script_opcode(self, client, mock_send, tmp_path):
        f = tmp_path / "worker.py"
        f.write_text("pass")
        mock_send.set_response("DEPLOY_SUCCESS")
        client.deploy_script(str(f))
        assert mock_send.calls[0][0] == OP_DEPLOY_SCRIPT

    def test_payload_starts_with_basename(self, client, mock_send, tmp_path):
        f = tmp_path / "worker.py"
        f.write_text("pass")
        mock_send.set_response("DEPLOY_SUCCESS")
        client.deploy_script(str(f))
        assert mock_send.calls[0][1].startswith("worker.py|")

    def test_missing_file_returns_error_without_sending(self, client, mock_send):
        result = client.deploy_script("/no/such/script.py")
        assert result.startswith("ERROR")
        assert len(mock_send.calls) == 0
