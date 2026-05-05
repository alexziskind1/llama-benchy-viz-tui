"""JSONL source reader.

Spawn a background thread that pulls JSONL lines from a file (with
tail-follow on EOF) or stdin, parses each into an `Envelope`, and pushes
parsed envelopes onto a `queue.Queue`. The main thread drains the queue
each render tick.
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Optional

from . import schema


@dataclass
class StdinSource:
    """Read from process stdin until EOF."""


@dataclass
class FileSource:
    """Read from a file, tail-following past EOF (`tail -f` semantics)."""

    path: Path


Source = StdinSource | FileSource

# Sentinel pushed when the reader thread exits — used by the UI to decide
# whether the input is exhausted.
EOF_SENTINEL: object = object()


def spawn(source: Source, q: "queue.Queue", *, follow_poll_s: float = 0.15) -> threading.Thread:
    """Start a reader thread. Returns the (already-started) thread.

    The thread parses JSONL lines and pushes `schema.Envelope` instances
    onto ``q``. When the input is exhausted (stdin EOF; file EOF in
    non-follow mode), the thread pushes ``EOF_SENTINEL`` then exits.
    Malformed lines are silently dropped.
    """
    t = threading.Thread(
        target=_run,
        args=(source, q, follow_poll_s),
        name="viz-tui-reader",
        daemon=True,
    )
    t.start()
    return t


def _run(source: Source, q: "queue.Queue", follow_poll_s: float) -> None:
    try:
        if isinstance(source, StdinSource):
            _read_loop(sys.stdin, q, follow=False, follow_poll_s=follow_poll_s)
        else:
            with open(source.path, "r") as f:
                _read_loop(f, q, follow=True, follow_poll_s=follow_poll_s)
    except Exception:
        # Don't crash the UI. The user will see "no events" and can
        # investigate.
        pass
    finally:
        try:
            q.put(EOF_SENTINEL)
        except Exception:
            pass


def _read_loop(
    f: IO[str],
    q: "queue.Queue",
    *,
    follow: bool,
    follow_poll_s: float,
) -> None:
    while True:
        line = f.readline()
        if line == "":
            if not follow:
                return
            time.sleep(follow_poll_s)
            continue
        env = schema.parse(line)
        if env is not None:
            q.put(env)


def make_source(path: Optional[str]) -> Source:
    """Translate the user-facing ``[PATH]`` argument into a `Source`.

    None or "-" → stdin. Anything else → file (tail-follow)."""
    if path is None or path == "-":
        return StdinSource()
    return FileSource(path=Path(path))
