"""Renderer layer — turn a ViewModel into a frame on screen.

Multiple renderers can coexist. The TUI is the reference implementation;
future web/native renderers consume the same ``ViewModel`` and produce
their own primitives.

A renderer must:
  - take a ViewModel (from view.compose.build_view_model)
  - return / produce a frame in its native format
  - not import benchmark or domain logic beyond `view.*` types

Public API:
    from llama_benchy_viz_tui.renderer.tui import render_view_model
"""
