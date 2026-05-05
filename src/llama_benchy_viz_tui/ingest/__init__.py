"""Ingest layer — wire-format readers + schema parsing.

Currently consumes only the JSONL stream produced by
``llama-benchy --emit-progress``. Future PRs may add additional sources
(e.g. ``BenchmarkReport JSON`` from ``--save-result --format json``) — they
should also funnel into the same `Envelope` type so the domain layer doesn't
need to know which surface it came from.

The ingest layer has **no Rich/UI dependencies**. It's the boundary between
"untyped wire format" and "typed domain events that the rest of the app
consumes". Renderer-agnostic by design.
"""

from .reader import EOF_SENTINEL, FileSource, Source, StdinSource, make_source, spawn
from .schema import Envelope, parse

__all__ = [
    "EOF_SENTINEL",
    "Envelope",
    "FileSource",
    "Source",
    "StdinSource",
    "make_source",
    "parse",
    "spawn",
]
