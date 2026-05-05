"""Parsed representation of `llama-benchy-progress.v1` envelopes.

This module is responsible for turning a JSON-decoded dict into a typed
record the rest of the app can consume, and for rejecting envelopes from
incompatible schema versions.

Spec: https://github.com/eugr/llama-benchy/blob/main/docs/progress-schema.md
"""

from __future__ import annotations

# TODO: define dataclasses for Header, RequestStart, RequestFirstToken,
# Tokens, RequestEnd, BenchComplete and a `parse(line: str) -> Envelope`
# helper. Reject lines whose `schema` field doesn't start with
# "llama-benchy-progress.v1".
