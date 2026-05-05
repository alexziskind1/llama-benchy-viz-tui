"""Live terminal dashboard for llama-benchy benchmarks.

Consumes the ``llama-benchy --emit-progress`` JSONL stream and renders a
real-time dashboard. Schema:
https://github.com/eugr/llama-benchy/blob/main/docs/progress-schema.md
"""

__version__ = "0.1.0"
SUPPORTED_SCHEMA = "llama-benchy-progress.v1"

__all__ = ["__version__", "SUPPORTED_SCHEMA"]
