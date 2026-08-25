"""CLI process-group lifecycle for adjudicate-workbench."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mtg_loop_engine.cli import run_managed_subprocess


def test_run_managed_subprocess_propagates_exit_code():
    assert run_managed_subprocess([sys.executable, "-c", "raise SystemExit(7)"]) == 7


def test_run_managed_subprocess_sigint_reaps_child(tmp_path: Path):
    """SIGINT on the manager must tear down the Streamlit-like child group."""
    ready = tmp_path / "ready"
    child = (
        "import os, time\n"
        "from pathlib import Path\n"
        f"Path({str(ready)!r}).write_text(str(os.getpid()), encoding='utf-8')\n"
        "time.sleep(60)\n"
    )
    manager = (
        "import sys\n"
        "from mtg_loop_engine.cli import run_managed_subprocess\n"
        "raise SystemExit(run_managed_subprocess("
        f"[sys.executable, '-c', {child!r}], timeout_after_term=2.0))\n"
    )
    mgr = subprocess.Popen(
        [sys.executable, "-c", manager],
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    try:
        deadline = time.time() + 10
        while not ready.exists():
            if mgr.poll() is not None:
                raise AssertionError("manager exited before child locked marker")
            if time.time() > deadline:
                raise AssertionError("timed out waiting for child marker")
            time.sleep(0.05)
        child_pid = int(ready.read_text(encoding="utf-8"))
        os.kill(mgr.pid, signal.SIGINT)
        mgr.wait(timeout=15)
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            pytest.fail(f"orphan child still alive: {child_pid}")
    finally:
        if mgr.poll() is None:
            mgr.kill()
            mgr.wait(timeout=5)
