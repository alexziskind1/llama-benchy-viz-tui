"""JSONL source reader.

Reads from a file (tail-follow on EOF) or stdin in a background thread,
parses each line as a `schema.Envelope`, and forwards events on a channel
to the UI thread.
"""

from __future__ import annotations

# TODO: implement `spawn(source, tx)` returning a thread handle, where
# `source` is one of `Source.Stdin` or `Source.File(path)`. Stdin → terminate
# on EOF. File → poll-and-retry on EOF for tail-follow semantics.
