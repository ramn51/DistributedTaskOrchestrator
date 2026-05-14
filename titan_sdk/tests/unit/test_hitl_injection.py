"""
Unit tests for TitanClient._inject_hitl_gates().

Pure graph-rewiring logic — no server required.
store_put is mocked to avoid socket calls triggered during gate injection.
"""
import pytest
from titan_sdk.titan_sdk import TitanClient, TitanJob


@pytest.fixture(autouse=True)
def no_store_put(monkeypatch):
    """Suppress the store_put call that clears stale HITL state."""
    monkeypatch.setattr(TitanClient, "store_put", lambda self, k, v: "OK")


class TestNoHitlMessage:

    def test_passthrough_unchanged(self, client, make_job):
        jobs = [make_job("a"), make_job("b", parents=["a"])]
        result = client._inject_hitl_gates(jobs)
        assert [j.id for j in result] == ["a", "b"]

    def test_count_unchanged(self, client, make_job):
        jobs = [make_job("a"), make_job("b"), make_job("c")]
        assert len(client._inject_hitl_gates(jobs)) == 3


class TestSingleGateInjection:

    def test_gate_inserted(self, client, make_job):
        jobs = [make_job("preprocess", hitl_message="Approve?"), make_job("train", parents=["preprocess"])]
        result = client._inject_hitl_gates(jobs)
        ids = [j.id for j in result]
        assert "hitl-gate-preprocess" in ids

    def test_total_job_count_increases_by_one(self, client, make_job):
        jobs = [make_job("preprocess", hitl_message="Approve?"), make_job("train", parents=["preprocess"])]
        assert len(client._inject_hitl_gates(jobs)) == 3

    def test_gate_positioned_after_source(self, client, make_job):
        jobs = [make_job("preprocess", hitl_message="Approve?"), make_job("train", parents=["preprocess"])]
        result = client._inject_hitl_gates(jobs)
        ids = [j.id for j in result]
        assert ids.index("hitl-gate-preprocess") > ids.index("preprocess")

    def test_gate_parent_is_source_job(self, client, make_job):
        jobs = [make_job("preprocess", hitl_message="Approve?"), make_job("train", parents=["preprocess"])]
        result = client._inject_hitl_gates(jobs)
        gate = next(j for j in result if j.id == "hitl-gate-preprocess")
        assert gate.parents == ["preprocess"]

    def test_downstream_rewired_to_gate(self, client, make_job):
        jobs = [make_job("preprocess", hitl_message="Approve?"), make_job("train", parents=["preprocess"])]
        result = client._inject_hitl_gates(jobs)
        train = next(j for j in result if j.id == "train")
        assert train.parents == ["hitl-gate-preprocess"]

    def test_unrelated_job_parents_unchanged(self, client, make_job):
        jobs = [
            make_job("a"),
            make_job("b", hitl_message="Check?"),
            make_job("c", parents=["a"]),  # depends on a, not b
        ]
        result = client._inject_hitl_gates(jobs)
        c = next(j for j in result if j.id == "c")
        assert c.parents == ["a"]

    def test_gate_args_contain_gate_id(self, client, make_job):
        jobs = [make_job("step1", hitl_message="Approve before training")]
        result = client._inject_hitl_gates(jobs)
        gate = next(j for j in result if "hitl-gate" in j.id)
        assert "hitl-gate-step1" in gate.args

    def test_gate_args_contain_max_wait(self, client, make_job):
        jobs = [make_job("step1", hitl_message="Approve?", max_wait_seconds=900)]
        result = client._inject_hitl_gates(jobs)
        gate = next(j for j in result if "hitl-gate" in j.id)
        assert "900" in gate.args

    def test_gate_args_contain_message(self, client, make_job):
        jobs = [make_job("step1", hitl_message="Please approve now")]
        result = client._inject_hitl_gates(jobs)
        gate = next(j for j in result if "hitl-gate" in j.id)
        assert "Please approve now" in gate.args

    def test_pipe_in_message_sanitised(self, client, make_job):
        """Pipe in hitl_message would corrupt the wire format."""
        jobs = [make_job("step1", hitl_message="Approve|Reject")]
        result = client._inject_hitl_gates(jobs)
        gate = next(j for j in result if "hitl-gate" in j.id)
        assert "Approve|Reject" not in gate.args
        assert "Approve Reject" in gate.args

    def test_gate_inherits_priority(self, client, make_job):
        jobs = [make_job("step1", hitl_message="Check", priority=9)]
        result = client._inject_hitl_gates(jobs)
        gate = next(j for j in result if "hitl-gate" in j.id)
        assert gate.priority == 9


class TestMultipleGates:

    def test_two_gates_inserted(self, client, make_job):
        jobs = [
            make_job("a", hitl_message="Gate A"),
            make_job("b", hitl_message="Gate B"),
            make_job("c", parents=["a", "b"]),
        ]
        result = client._inject_hitl_gates(jobs)
        ids = [j.id for j in result]
        assert "hitl-gate-a" in ids
        assert "hitl-gate-b" in ids

    def test_downstream_rewired_to_both_gates(self, client, make_job):
        jobs = [
            make_job("a", hitl_message="Gate A"),
            make_job("b", hitl_message="Gate B"),
            make_job("c", parents=["a", "b"]),
        ]
        result = client._inject_hitl_gates(jobs)
        c = next(j for j in result if j.id == "c")
        assert set(c.parents) == {"hitl-gate-a", "hitl-gate-b"}
