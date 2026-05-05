"""Entry point for the `llama-benchy-viz-tui` console script."""

from __future__ import annotations

import argparse
import queue
import sys
import time
from typing import Optional

from rich.console import Console
from rich.live import Live

from . import SUPPORTED_SCHEMA, __version__
from .ingest import reader as reader_mod
from .input_kbd import KeyboardReader
from .domain import AppState
from .ui import render

DEFAULT_FPS = 8.0


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="llama-benchy-viz-tui",
        description=(
            "Live terminal dashboard for llama-benchy benchmarks. Consumes "
            f"the --emit-progress JSONL stream (schema: {SUPPORTED_SCHEMA})."
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
        help=(
            "Exit automatically `--hold N` seconds after a bench_complete event. "
            "Without this flag the dashboard stays on screen until Ctrl+C."
        ),
    )
    parser.add_argument(
        "--hold",
        type=int,
        default=10,
        metavar="N",
        help="With --auto-exit: seconds to hold the final frame before exiting (default: 10).",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="benchmark",
        help="Header label for the dashboard (default: 'benchmark').",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=DEFAULT_FPS,
        help=f"Render frame-rate cap (default: {DEFAULT_FPS}).",
    )
    parser.add_argument(
        "--show-events",
        action="store_true",
        help=(
            "Show the rolling events / audit log panel. Off by default — "
            "useful for debugging multi-target runs, errors, or long sweeps."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    source = reader_mod.make_source(args.path)
    q: "queue.Queue" = queue.Queue()
    reader_mod.spawn(source, q)

    state = AppState(benchmark_name=args.name, show_events=args.show_events)
    console = Console()
    keyboard = KeyboardReader()
    keyboard.start()  # silently no-ops if /dev/tty isn't available

    period = 1.0 / max(args.fps, 1.0)
    finished_at: Optional[float] = None
    eof = False

    def renderable():
        size = console.size
        return render(state.snapshot(), console_width=size.width, console_height=size.height)

    try:
        with Live(
            renderable(),
            console=console,
            auto_refresh=False,
            screen=True,
            transient=False,
        ) as live:
            while True:
                drained = _drain_queue(q, state)
                if drained is _DRAIN_EOF:
                    eof = True

                # Drain keyboard events and dispatch to scroll / quit handlers.
                if keyboard.is_running:
                    for ev in keyboard.poll():
                        name = ev.name
                        if name in ("q", "ctrl_c"):
                            raise KeyboardInterrupt
                        elif name == "down":
                            state.scroll_cells(1)
                        elif name == "up":
                            state.scroll_cells(-1)
                        elif name == "page_down":
                            state.scroll_cells(10)
                        elif name == "page_up":
                            state.scroll_cells(-10)
                        elif name == "home":
                            state.scroll_cells_home()
                        elif name == "end":
                            state.scroll_cells_end()

                if state.finished and finished_at is None:
                    finished_at = time.monotonic()

                # Single refresh per tick — Live's auto-refresh is off so we
                # control paint timing and avoid double-paints with the main
                # loop's own pacing.
                live.update(renderable(), refresh=True)

                # Exit policy:
                #   * --auto-exit + bench_complete seen + hold elapsed → exit
                #   * Otherwise stay on screen forever; user uses Ctrl+C
                #     to leave. EOF without bench_complete (producer died)
                #     also stays — the user wants to see the partial state.
                if (
                    args.auto_exit
                    and finished_at is not None
                    and (time.monotonic() - finished_at) >= args.hold
                ):
                    break

                time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        keyboard.stop()

    return 0


_DRAIN_EOF: object = object()


def _drain_queue(q: "queue.Queue", state: AppState):
    """Pull every queued envelope into state. Returns _DRAIN_EOF if the
    sentinel was seen, else None."""
    saw_eof = False
    while True:
        try:
            item = q.get_nowait()
        except queue.Empty:
            break
        if item is reader_mod.EOF_SENTINEL:
            saw_eof = True
            continue
        try:
            state.ingest(item)
        except Exception as e:
            # Never let a bad event take down the UI.
            print(f"ingest error: {e}", file=sys.stderr)
    return _DRAIN_EOF if saw_eof else None


if __name__ == "__main__":
    raise SystemExit(main())
