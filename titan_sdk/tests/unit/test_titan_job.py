"""
Unit tests for TitanJob — wire format serialisation and validation.

No server required. All tests use temporary files created by tmp_path.
"""
import base64
import os
import pytest

from titan_sdk.titan_sdk import TitanJob


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(job):
    """Split a job's to_string() output into fields for easy assertion."""
    return job.to_string().split("|")


# ---------------------------------------------------------------------------
# RUN_PAYLOAD format
# ---------------------------------------------------------------------------

class TestRunPayloadFormat:

    def test_job_id_is_first_field(self, make_job):
        assert parse(make_job("my-job"))[0] == "my-job"

    def test_header_is_run_payload(self, make_job):
        assert parse(make_job("j"))[1] == "RUN_PAYLOAD"

    def test_filename_is_basename_only(self, tmp_path):
        """Full absolute paths must be stripped to basename — master has no access to local paths."""
        subdir = tmp_path / "deep"
        subdir.mkdir()
        path = subdir / "worker.py"
        path.write_text("pass")
        job = TitanJob(job_id="j", filename=str(path))
        assert parse(job)[2] == "worker.py"

    def test_args_field(self, make_job):
        job = make_job("j", args="--lr 0.01 --epochs 10")
        assert parse(job)[3] == "--lr 0.01 --epochs 10"

    def test_empty_args_field(self, make_job):
        job = make_job("j", args="")
        assert parse(job)[3] == ""

    def test_payload_is_valid_base64(self, make_job):
        fields = parse(make_job("j"))
        b64 = fields[4]
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0

    def test_payload_decodes_to_script_content(self, tmp_script):
        path = tmp_script(content="x = 42\n")
        job = TitanJob(job_id="j", filename=path)
        decoded = base64.b64decode(parse(job)[4]).decode()
        assert "x = 42" in decoded

    def test_requirement_field_default(self, make_job):
        assert parse(make_job("j"))[5] == "GENERAL"

    def test_requirement_field_custom(self, make_job):
        job = make_job("j", requirement="GPU")
        assert parse(job)[5] == "GPU"

    def test_priority_field(self, make_job):
        job = make_job("j", priority=7)
        assert parse(job)[6] == "7"

    def test_delay_field_default(self, make_job):
        assert parse(make_job("j"))[7] == "0"

    def test_parents_empty(self, make_job):
        assert parse(make_job("j"))[8] == "[]"

    def test_parents_single(self, make_job):
        job = make_job("j", parents=["a"])
        assert parse(job)[8] == "[a]"

    def test_parents_multiple(self, make_job):
        job = make_job("j", parents=["a", "b", "c"])
        assert parse(job)[8] == "[a,b,c]"

    def test_no_affinity_suffix_by_default(self, make_job):
        assert not make_job("j").to_string().endswith("|AFFINITY")

    def test_affinity_suffix_appended(self, make_job):
        assert make_job("j", affinity=True).to_string().endswith("|AFFINITY")


# ---------------------------------------------------------------------------
# Pipe sanitisation — a pipe in args/requirement would corrupt the wire format
# ---------------------------------------------------------------------------

class TestPipeSanitisation:

    def test_pipe_in_args_replaced_with_space(self, make_job):
        job = make_job("j", args="foo|bar|baz")
        assert "foo bar baz" in job.to_string()
        assert "foo|bar" not in job.to_string()

    def test_pipe_in_requirement_stripped(self, make_job):
        job = make_job("j", requirement="GPU|HACK")
        assert "GPUHACK" in job.to_string()
        assert "GPU|HACK" not in job.to_string()


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

class TestFileLoading:

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            TitanJob(job_id="j", filename="/nonexistent/path/script.py")

    def test_error_message_includes_path(self):
        try:
            TitanJob(job_id="j", filename="/no/such/file.py")
        except FileNotFoundError as e:
            assert "/no/such/file.py" in str(e)

    def test_relative_path_resolved(self, tmp_path, monkeypatch):
        """A relative path that resolves from cwd should work."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "relative.py").write_text("pass")
        job = TitanJob(job_id="j", filename="relative.py")
        assert parse(job)[2] == "relative.py"


# ---------------------------------------------------------------------------
# Archive / SERVICE jobs
# ---------------------------------------------------------------------------

class TestArchiveJob:

    def test_archive_header_is_run_archive(self, make_job, tmp_script):
        path = tmp_script("pkg.zip")
        job = TitanJob(job_id="j", filename="pkg.zip/entry.py", is_archive=True)
        assert parse(job)[1] == "RUN_ARCHIVE"

    def test_archive_payload_is_remote_asset_sentinel(self, tmp_script):
        job = TitanJob(job_id="j", filename="pkg.zip/entry.py", is_archive=True)
        # is_archive skips local file loading — payload slot is sentinel
        assert job.payload_b64 == "REMOTE_ASSET"

    def test_service_header(self, tmp_script):
        path = tmp_script("server.py")
        job = TitanJob(job_id="j", filename=path, job_type="SERVICE", port=8080)
        assert parse(job)[1] == "DEPLOY_PAYLOAD"
