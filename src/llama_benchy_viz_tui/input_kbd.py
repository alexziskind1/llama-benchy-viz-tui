"""Keyboard input via `/dev/tty` (Unix only).

Opens `/dev/tty` directly so we don't conflict with stdin (which the JSONL
reader uses in pipe mode). A background thread reads bytes, parses key
events, and pushes them onto a queue the UI thread drains.

Cleanup is registered via `atexit` so the terminal is restored to its
prior cooked-mode settings even if the process exits abnormally
(KeyboardInterrupt propagating out, sys.exit, etc.). Terminal raw mode
keeps `ISIG` enabled so Ctrl+C still raises SIGINT — we don't try to be
cleverer than the kernel here.
"""

from __future__ import annotations

import atexit
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class KeyEvent:
    name: str  # one of: up, down, page_up, page_down, home, end, q, ctrl_c


class KeyboardReader:
    def __init__(self) -> None:
        self._tty_fd: Optional[int] = None
        self._old_attrs = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[KeyEvent]" = queue.Queue()
        self._atexit_registered = False

    @property
    def is_running(self) -> bool:
        return self._tty_fd is not None

    def start(self) -> bool:
        """Try to open /dev/tty in raw mode. Returns False if no tty."""
        if self._tty_fd is not None:
            return True
        try:
            import termios  # noqa: F401  (POSIX-only)
        except ImportError:
            return False
        try:
            self._tty_fd = os.open("/dev/tty", os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            self._tty_fd = None
            return False
        if not self._configure_raw_mode():
            self._safe_close()
            return False
        if not self._atexit_registered:
            atexit.register(self.stop)
            self._atexit_registered = True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="viz-tui-keys", daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._tty_fd is None:
            return
        self._stop.set()
        t = self._thread
        self._thread = None
        if t is not None:
            t.join(timeout=0.5)
        self._restore_attrs()
        self._safe_close()

    def poll(self) -> List[KeyEvent]:
        """Drain queued events without blocking."""
        events: List[KeyEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events

    # internals
    def _configure_raw_mode(self) -> bool:
        import termios

        try:
            self._old_attrs = termios.tcgetattr(self._tty_fd)
        except termios.error:
            return False
        new_attrs = list(self._old_attrs)
        # Disable canonical line buffering and local echo. Keep ISIG so
        # Ctrl+C still delivers SIGINT to the foreground process group.
        new_attrs[3] = new_attrs[3] & ~(termios.ICANON | termios.ECHO)
        try:
            new_attrs[6][termios.VMIN] = 0   # non-blocking
            new_attrs[6][termios.VTIME] = 0
        except (IndexError, AttributeError):
            pass
        try:
            termios.tcsetattr(self._tty_fd, termios.TCSANOW, new_attrs)
        except termios.error:
            return False
        return True

    def _restore_attrs(self) -> None:
        if self._old_attrs is None or self._tty_fd is None:
            return
        try:
            import termios

            termios.tcsetattr(self._tty_fd, termios.TCSANOW, self._old_attrs)
        except Exception:
            pass

    def _safe_close(self) -> None:
        if self._tty_fd is not None:
            try:
                os.close(self._tty_fd)
            except OSError:
                pass
            self._tty_fd = None

    def _run(self) -> None:
        buf = b""
        fd = self._tty_fd
        while not self._stop.is_set() and fd is not None:
            try:
                data = os.read(fd, 32)
            except (BlockingIOError, OSError):
                data = b""
            if not data:
                time.sleep(0.05)
                continue
            buf += data
            while buf:
                ev, consumed = _parse_key(buf)
                if consumed == 0:
                    break
                if ev is not None:
                    self._queue.put(ev)
                buf = buf[consumed:]


def _parse_key(buf: bytes):
    """Return (KeyEvent or None, bytes consumed). 0 = need more bytes."""
    if not buf:
        return None, 0
    # Multi-byte escape sequences.
    if buf[:3] == b"\x1b[A":
        return KeyEvent("up"), 3
    if buf[:3] == b"\x1b[B":
        return KeyEvent("down"), 3
    if buf[:4] == b"\x1b[5~":
        return KeyEvent("page_up"), 4
    if buf[:4] == b"\x1b[6~":
        return KeyEvent("page_down"), 4
    if buf[:3] in (b"\x1bOH", b"\x1b[H"):
        return KeyEvent("home"), 3
    if buf[:3] in (b"\x1bOF", b"\x1b[F"):
        return KeyEvent("end"), 3
    # Lone ESC: maybe an incomplete sequence — wait for more bytes if buffer
    # is short, otherwise treat as a single byte to avoid stuckness.
    if buf[:1] == b"\x1b" and len(buf) < 4:
        return None, 0

    c = buf[:1]
    if c == b"q":
        return KeyEvent("q"), 1
    if c == b"\x03":  # Ctrl+C as a literal byte (in case ISIG is off)
        return KeyEvent("ctrl_c"), 1
    if c == b"j":
        return KeyEvent("down"), 1
    if c == b"k":
        return KeyEvent("up"), 1
    if c == b"g":
        return KeyEvent("home"), 1
    if c == b"G":
        return KeyEvent("end"), 1
    return None, 1
