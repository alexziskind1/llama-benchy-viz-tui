"""Entry point for the `llama-benchy-viz-tui` console script."""

from __future__ import annotations

import argparse
import sys

from . import SUPPORTED_SCHEMA, __version__


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="llama-benchy-viz-tui",
        description=(
            "Live terminal dashboard for llama-benchy benchmarks. Consumes "
            "the --emit-progress JSONL stream (schema: %s)." % SUPPORTED_SCHEMA
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        metavar="PATH",
        help="JSONL file to tail-follow, or '-' / omitted to read stdin.",
    )
    parser.add_argument(
        "--auto-exit",
        action="store_true",
        help="Exit automatically after seeing a bench_complete event.",
    )
    parser.add_argument(
        "--hold",
        type=int,
        default=10,
        metavar="N",
        help="Seconds to keep the final frame on screen after bench_complete (default: 10).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # TODO: open source via reader.spawn, build state, run Rich Live render
    # loop, handle q/Esc/Ctrl+C, exit on bench_complete + hold.
    print(
        f"llama-benchy-viz-tui {__version__} — scaffold only, UI not yet implemented.",
        file=sys.stderr,
    )
    print(f"  args: {vars(args)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
