"""
Shared fixtures for Titan SDK tests.
"""
import pytest
import sys
import os

# Make sure the SDK is importable regardless of where pytest is invoked from
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from titan_sdk.titan_sdk import TitanClient, TitanJob


@pytest.fixture
def tmp_script(tmp_path):
    """Factory: creates a minimal .py file in tmp_path and returns its path string."""
    def _make(name="worker.py", content="print('hello')"):
        p = tmp_path / name
        p.write_text(content)
        return str(p)
    return _make


@pytest.fixture
def make_job(tmp_script):
    """Factory: returns a TitanJob backed by a real temp file."""
    def _make(job_id, name=None, parents=None, priority=1,
              requirement="GENERAL", args="", affinity=False,
              hitl_message=None, max_wait_seconds=172800):
        filename = tmp_script(name or f"{job_id}.py")
        return TitanJob(
            job_id=job_id,
            filename=filename,
            parents=parents or [],
            priority=priority,
            requirement=requirement,
            args=args,
            affinity=affinity,
            hitl_message=hitl_message,
            max_wait_seconds=max_wait_seconds,
        )
    return _make


@pytest.fixture
def client():
    return TitanClient()
