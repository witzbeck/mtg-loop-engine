"""Process-group lifecycle for long-running CLI subprocesses (e.g. Streamlit)."""

from __future__ import annotations

import os
import signal
import subprocess
import time


def run_managed_subprocess(argv: list[str], *, timeout_after_term: float = 5.0) -> int:
    """Run ``argv`` in its own process group; forward stop signals and reap children.

    Plain ``subprocess.call`` under ``uv run`` often leaves Streamlit alive after the
    wrapper exits (Ctrl+C / terminal close), which keeps the DuckDB file lock.
    Own-session + killpg closes that gap.
    """
    proc = subprocess.Popen(argv, start_new_session=True)

    def _stop_child(sig: int = signal.SIGTERM) -> None:
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            pass

    def _forward(signum: int, _frame: object) -> None:
        _stop_child(signum if signum != signal.SIGHUP else signal.SIGTERM)
        raise SystemExit(128 + (signum if signum >= 0 else 0))

    prev: dict[int, object] = {}
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        prev[sig] = signal.signal(sig, _forward)
    try:
        return int(proc.wait())
    finally:
        for sig, handler in prev.items():
            signal.signal(sig, handler)  # type: ignore[arg-type]
        if proc.poll() is None:
            _stop_child(signal.SIGTERM)
            deadline = time.monotonic() + timeout_after_term
            while proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            if proc.poll() is None:
                _stop_child(signal.SIGKILL)
                proc.wait()
