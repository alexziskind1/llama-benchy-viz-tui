"""TUI renderer — reference implementation.

Public API:

    from llama_benchy_viz_tui.renderer.tui import render_view_model

The single entry point takes a ``ViewModel`` (from ``view.compose``) and
returns a Rich ``Layout`` ready to drop into ``rich.live.Live`` or
``Console.print``.
"""

from .layout import render_view_model

__all__ = ["render_view_model"]
