"""Parsed representation of the `llama-benchy-progress.v1` JSONL stream.

Every line in the stream is a JSON object with at minimum ``schema``,
``type``, and ``ts`` fields. Unknown ``type`` values are tolerated (returned
as ``Envelope.kind == "<unknown>"``) so a future schema add doesn't break us.
A wrong ``schema`` field is treated as fatal-for-this-line and silently
skipped — see ``parse``'s return contract.

Spec: https://github.com/eugr/llama-benchy/blob/main/docs/progress-schema.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from . import SUPPORTED_SCHEMA


@dataclass
class Envelope:
    """One parsed JSONL line."""

    schema: str
    kind: str
    ts: float

    # Most fields are optional — only those relevant for ``kind`` are populated.
    request_id: Optional[int] = None
    model: str = ""
    base_url: str = ""
    prompt_size: int = 0
    response_size: int = 0
    context_size: int = 0
    concurrency: int = 0
    run_index: int = 0
    target_label: str = ""

    ttft_s: Optional[float] = None
    ttfr_s: Optional[float] = None
    count: int = 0
    snippet: str = ""

    total_tokens: int = 0
    prompt_tokens: int = 0
    decode_seconds: float = 0.0
    error: str = ""

    llama_benchy_version: str = ""
    latency_s: Optional[float] = None
    mode: str = ""

    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_known_kind(self) -> bool:
        return self.kind in {
            "header",
            "request_start",
            "request_first_response",
            "request_first_token",
            "tokens",
            "request_end",
            "bench_complete",
            "latency_measured",
        }


def parse(line: str) -> Optional[Envelope]:
    """Parse one JSONL line. Returns ``None`` for malformed JSON, lines that
    don't carry our schema string, or empty input.

    Unknown ``type`` values still return an ``Envelope`` so callers can
    decide how to react (the typical choice is "ignore")."""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except (TypeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    schema = obj.get("schema")
    if schema != SUPPORTED_SCHEMA:
        return None
    kind = obj.get("type") or "<unknown>"
    return Envelope(
        schema=schema,
        kind=kind,
        ts=float(obj.get("ts", 0.0)),
        request_id=_opt_int(obj.get("request_id")),
        model=str(obj.get("model", "")),
        base_url=str(obj.get("base_url", "")),
        prompt_size=int(obj.get("prompt_size", 0) or 0),
        response_size=int(obj.get("response_size", 0) or 0),
        context_size=int(obj.get("context_size", 0) or 0),
        concurrency=int(obj.get("concurrency", 0) or 0),
        run_index=int(obj.get("run_index", 0) or 0),
        target_label=str(obj.get("target_label", "")),
        ttft_s=_opt_float(obj.get("ttft_s")),
        ttfr_s=_opt_float(obj.get("ttfr_s")),
        count=int(obj.get("count", 0) or 0),
        snippet=str(obj.get("snippet", "")),
        total_tokens=int(obj.get("total_tokens", 0) or 0),
        prompt_tokens=int(obj.get("prompt_tokens", 0) or 0),
        decode_seconds=float(obj.get("decode_seconds", 0.0) or 0.0),
        error=str(obj.get("error", "")),
        llama_benchy_version=str(obj.get("llama_benchy_version", "")),
        latency_s=_opt_float(obj.get("latency_s")),
        mode=str(obj.get("mode", "")),
        raw=obj,
    )


def _opt_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _opt_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
