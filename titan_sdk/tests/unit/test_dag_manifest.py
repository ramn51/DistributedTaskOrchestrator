"""
Unit tests for TitanClient._write_dag_manifest().

Tests the JSON structure written to .titan_dag_manifest.json.
Uses monkeypatch.chdir(tmp_path) to isolate file writes from the real project root.
"""
import json
import pytest
from titan_sdk.titan_sdk import TitanClient


@pytest.fixture(autouse=True)
def isolated_dir(tmp_path, monkeypatch):
    """Each test gets a clean working directory so manifests don't bleed."""
    monkeypatch.chdir(tmp_path)


def read_manifest(tmp_path):
    return json.loads((tmp_path / ".titan_dag_manifest.json").read_text())


class TestManifestStructure:

    def test_manifest_file_created(self, client, make_job, tmp_path):
        client._write_dag_manifest("MY_DAG", [make_job("a")])
        assert (tmp_path / ".titan_dag_manifest.json").exists()

    def test_job_entry_has_dag_name(self, client, make_job, tmp_path):
        client._write_dag_manifest("MY_DAG", [make_job("a")])
        manifest = read_manifest(tmp_path)
        assert manifest["DAG-a"]["dag"] == "MY_DAG"

    def test_job_entry_prefixed_with_dag(self, client, make_job, tmp_path):
        client._write_dag_manifest("D", [make_job("step1")])
        manifest = read_manifest(tmp_path)
        assert "DAG-step1" in manifest

    def test_deps_mapped_correctly(self, client, make_job, tmp_path):
        jobs = [make_job("a"), make_job("b", parents=["a"])]
        client._write_dag_manifest("D", jobs)
        manifest = read_manifest(tmp_path)
        assert manifest["DAG-b"]["deps"] == ["DAG-a"]

    def test_root_job_has_empty_deps(self, client, make_job, tmp_path):
        client._write_dag_manifest("D", [make_job("root")])
        manifest = read_manifest(tmp_path)
        assert manifest["DAG-root"]["deps"] == []

    def test_run_ts_present(self, client, make_job, tmp_path):
        client._write_dag_manifest("D", [make_job("a")])
        manifest = read_manifest(tmp_path)
        assert "run_ts" in manifest["DAG-a"]
        assert manifest["DAG-a"]["run_ts"] > 0

    def test_multiple_jobs_all_written(self, client, make_job, tmp_path):
        jobs = [make_job("a"), make_job("b"), make_job("c")]
        client._write_dag_manifest("D", jobs)
        manifest = read_manifest(tmp_path)
        assert "DAG-a" in manifest
        assert "DAG-b" in manifest
        assert "DAG-c" in manifest


class TestAgentRunId:

    def test_agent_run_id_stored_on_job(self, client, make_job, tmp_path):
        client._write_dag_manifest("D", [make_job("a")], agent_run_id="run42")
        manifest = read_manifest(tmp_path)
        assert manifest["DAG-a"]["agent_run_id"] == "run42"

    def test_no_agent_run_id_key_absent(self, client, make_job, tmp_path):
        client._write_dag_manifest("D", [make_job("a")])
        manifest = read_manifest(tmp_path)
        assert "agent_run_id" not in manifest["DAG-a"]

    def test_agent_run_summary_entry_created(self, client, make_job, tmp_path):
        client._write_dag_manifest("STAGE1", [make_job("a")], agent_run_id="run42")
        manifest = read_manifest(tmp_path)
        assert "__agent_run__run42" in manifest

    def test_agent_run_summary_contains_stage(self, client, make_job, tmp_path):
        client._write_dag_manifest("STAGE1", [make_job("a")], agent_run_id="run42")
        manifest = read_manifest(tmp_path)
        assert "STAGE1" in manifest["__agent_run__run42"]["stages"]

    def test_multiple_stages_accumulate(self, client, make_job, tmp_path):
        client._write_dag_manifest("STAGE1", [make_job("a")], agent_run_id="run42")
        client._write_dag_manifest("STAGE2", [make_job("b")], agent_run_id="run42")
        manifest = read_manifest(tmp_path)
        stages = manifest["__agent_run__run42"]["stages"]
        assert "STAGE1" in stages
        assert "STAGE2" in stages

    def test_duplicate_stage_not_added_twice(self, client, make_job, tmp_path):
        client._write_dag_manifest("STAGE1", [make_job("a")], agent_run_id="run42")
        client._write_dag_manifest("STAGE1", [make_job("b")], agent_run_id="run42")
        manifest = read_manifest(tmp_path)
        stages = manifest["__agent_run__run42"]["stages"]
        assert stages.count("STAGE1") == 1


class TestPayloadStorage:

    def test_payload_entry_stored(self, client, make_job, tmp_path):
        client._write_dag_manifest("D", [make_job("a")], dag_payload="a|RUN_PAYLOAD|...")
        manifest = read_manifest(tmp_path)
        assert "__payload__D" in manifest

    def test_existing_manifest_updated_not_overwritten(self, client, make_job, tmp_path):
        client._write_dag_manifest("D1", [make_job("a")])
        client._write_dag_manifest("D2", [make_job("b")])
        manifest = read_manifest(tmp_path)
        assert "DAG-a" in manifest
        assert "DAG-b" in manifest
