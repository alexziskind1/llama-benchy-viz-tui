"""End-to-end smoke test for all 4 dashboard modes.

Runs ``llama-benchy-viz-tui`` against synthetic fixtures under a
properly-sized pty, captures output, and asserts that mode-specific
landmarks appear on screen.

Covers both auto-detection (static-vs-live by ``bench_complete``,
single-vs-race by stream count) and explicit ``--mode`` overrides.

Usage:
    python -m tests.smoke

Exit code is 0 only when every check passes.
"""

from __future__ import annotations

import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VIZ = REPO / ".venv" / "bin" / "llama-benchy-viz-tui"

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

LANDMARKS: dict[str, list[str]] = {
    "static-single": [
        "STATIC · SINGLE", "PERFORMANCE — FINAL", "CELLS",
        "RUN METADATA", "FROZEN",
    ],
    "static-race": [
        "STATIC · RACE", "FINAL RANKING", "#1", "#2",
        "PERFORMANCE — FINAL", "RUN METADATA", "FROZEN",
    ],
    "live-single": [
        "LIVE · SINGLE", "LIVE PERFORMANCE", "CELLS",
    ],
    "live-race": [
        "LIVE · RACE", "LIVE RANKING", "#1", "#2", "LIVE PERFORMANCE",
    ],
}


def gen_fixture(scenario: str, out: Path, *, in_flight: bool = False) -> None:
    cmd = [sys.executable, "-m", "tests.gen", scenario, str(out)]
    if in_flight:
        cmd.append("--in-flight")
    subprocess.run(cmd, check=True, cwd=REPO)


def run_pty(
    args: list[str],
    *,
    rows: int = 50,
    cols: int = 220,
    wall_timeout: float = 3.5,
) -> tuple[int, str]:
    """Spawn args under a pty sized to (rows, cols), capture stdout/stderr.

    Sends SIGINT after ``wall_timeout`` seconds — required for in-flight
    fixtures where ``--auto-exit`` never trips because no
    ``bench_complete`` arrives.
    """
    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    p = subprocess.Popen(
        args, stdin=slave, stdout=slave, stderr=slave,
        close_fds=True, cwd=REPO,
    )
    os.close(slave)

    chunks: list[bytes] = []
    start = time.monotonic()
    sigint_sent = False
    while p.poll() is None:
        if not sigint_sent and (time.monotonic() - start) > wall_timeout:
            try:
                p.send_signal(signal.SIGINT)
            except ProcessLookupError:
                pass
            sigint_sent = True
        r, _, _ = select.select([master], [], [], 0.1)
        if r:
            try:
                d = os.read(master, 65536)
                if not d:
                    break
                chunks.append(d)
            except OSError:
                break

    while True:
        r, _, _ = select.select([master], [], [], 0.1)
        if not r:
            break
        try:
            d = os.read(master, 65536)
            if not d:
                break
            chunks.append(d)
        except OSError:
            break

    os.close(master)
    try:
        p.wait(timeout=2)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
    return p.returncode, b"".join(chunks).decode("utf-8", errors="replace")


def check(label: str, args: list[str], expected_mode: str) -> bool:
    rc, out = run_pty([str(VIZ), "--auto-exit", "--hold", "1", *args])
    plain = ANSI.sub("", out)
    expected = LANDMARKS[expected_mode]
    missing = [t for t in expected if t not in plain]
    ok = (rc in (0, -signal.SIGINT)) and not missing
    status = "PASS" if ok else "FAIL"
    detail = "" if not missing else f"  missing={missing!r}"
    print(f"  [{status}] {label} (rc={rc}){detail}")
    return ok


def main() -> int:
    if not VIZ.exists():
        print(f"ERROR: viz-tui not installed at {VIZ}", file=sys.stderr)
        print("Run: uv pip install -e . (from repo root)", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        single_done = d / "single-complete.jsonl"
        single_live = d / "single-inflight.jsonl"
        race2_done = d / "race-2-complete.jsonl"
        race2_live = d / "race-2-inflight.jsonl"

        gen_fixture("single", single_done)
        gen_fixture("single", single_live, in_flight=True)
        gen_fixture("race-2", race2_done)
        gen_fixture("race-2", race2_live, in_flight=True)

        results: list[bool] = []

        print("auto-detect")
        results.append(check(
            "static-single  (1 model, complete)",
            [str(single_done)], "static-single",
        ))
        results.append(check(
            "static-race    (2 models, complete)",
            [str(race2_done)], "static-race",
        ))
        results.append(check(
            "live-single    (1 model, in-flight)",
            [str(single_live)], "live-single",
        ))
        results.append(check(
            "live-race      (2 models, in-flight)",
            [str(race2_live)], "live-race",
        ))

        print("\n--mode override")
        for mode in ("static-single", "static-race", "live-single", "live-race"):
            fixture = single_done if "single" in mode else race2_done
            results.append(check(
                f"{mode:<14} (forced)",
                ["--mode", mode, str(fixture)], mode,
            ))

    total = len(results)
    passed = sum(results)
    print(f"\n{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
