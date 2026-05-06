# Architecture

The visualizer is layered so a future web/native frontend can reuse the
same domain + view code without dragging in Rich. Five layers, each
with no upward dependencies.

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 5: Renderer                                              │
│  - TUI (Rich, this package's reference impl)                    │
│  - web / native: future, plug into the same ViewModel           │
└────────────────────────────────────────────▲────────────────────┘
                                              │ ViewModel + LayoutSpec
┌─────────────────────────────────────────────┴───────────────────┐
│  Layer 4: View / dashboard composer                             │
│  - DashboardMode (4 modes) — auto-detected, --mode override     │
│  - ModuleSpec catalog (HeaderSpec, ChartSpec, …)                │
│  - LayoutSpec per mode (which modules in which region)          │
│  - compose: SessionState → ViewModel                            │
└────────────────────────────────────────────▲────────────────────┘
                                              │ Snapshot
┌─────────────────────────────────────────────┴───────────────────┐
│  Layer 3: Domain / state                                        │
│  - SlotState, CellState, MetricsSnapshot, EventEntry,           │
│    Snapshot, AppState (event-sourced store)                     │
│  - ranking / aggregation logic                                  │
│  - **No Rich/UI imports**                                       │
└────────────────────────────────────────────▲────────────────────┘
                                              │ Envelope
┌─────────────────────────────────────────────┴───────────────────┐
│  Layer 2: Ingest / wire-format                                  │
│  - JSONL reader (live tail-follow / replay)                     │
│  - Envelope schema parsing                                      │
└────────────────────────────────────────────▲────────────────────┘
                                              │ JSONL bytes
┌─────────────────────────────────────────────┴───────────────────┐
│  Layer 1: llama-benchy producer (separate repo)                 │
│  Schema: docs/progress-schema.md (in llama-benchy)              │
└─────────────────────────────────────────────────────────────────┘
```

## Source layout

```
src/llama_benchy_viz_tui/
├── ingest/             ← Layer 2
│   ├── schema.py       Envelope parsing
│   └── reader.py       tail-follow / stdin
├── domain/             ← Layer 3
│   ├── state.py        dataclasses (SlotState, Snapshot, …)
│   └── store.py        AppState (event-sourced)
├── view/               ← Layer 4
│   ├── mode.py         DashboardMode + auto-detect
│   ├── modules.py      ModuleSpec dataclasses
│   ├── layouts.py      LayoutSpec per mode
│   └── compose.py      Snapshot + Mode → ViewModel
├── renderer/           ← Layer 5
│   └── tui/
│       ├── modules.py  ModuleSpec → Rich Renderable adapters
│       └── layout.py   LayoutSpec + ViewModel → Rich Layout
├── chart.py            renderer-agnostic Braille line chart
├── input_kbd.py        /dev/tty raw-mode keyboard reader
├── ui.py               thin façade: Snapshot → ViewModel → Rich
└── __main__.py         CLI entry point + render loop
```

## Dashboard modes

Four modes pick distinct module sets and styling. Auto-detected from
``len(snap.slots)`` (single ↔ race) and ``snap.finished`` (live ↔ static);
overridable with ``--mode``.

|  Module          | static-single | static-race | live-single | live-race |
|------------------|---------------|-------------|-------------|-----------|
| Header           | ✓             | ✓           | ✓           | ✓         |
| Summary strip    | ✓ winners     | ✓ winners   | ✓ current   | ✓ live    |
| Model card       | ✓ (large)     | —           | ✓           | —         |
| Stream grid      | —             | ✓ (frozen)  | —           | ✓ (live)  |
| Live chart       | —             | —           | ✓           | ✓         |
| Static chart     | ✓             | ✓           | —           | —         |
| Ranking table    | —             | ✓           | —           | ✓         |
| Event log        | —             | —           | —           | ✓         |
| Run metadata     | ✓             | ✓           | —           | —         |
| Cells table      | ✓ (full sweep)| —           | ✓ (live)    | —         |
| Footer           | ✓             | ✓           | ✓           | ✓         |

## Region wiring

Every mode uses the same conceptual regions; modules go to the same
region across modes when they appear:

```
┌──────────────── HEADER ─────────────────┐
├──────────────── SUMMARY ────────────────┤
│  MAIN_LEFT          │  MAIN_RIGHT       │
│  (cards / grid)     │  (chart)          │
│                     ├───────────────────┤
│                     │ MAIN_RIGHT_BOTTOM │
│                     │ (ranking/events)  │
├─────────────── DETAIL_BAND ─────────────┤
│  (cells / metadata, mode-conditional)   │
├─────────────── FOOTER ──────────────────┤
```

## Live ↔ static is not "freeze the live version"

| Concern | Live | Static |
|---|---|---|
| Chart window | Trailing 120 s | Full run, axis fixed |
| Y-axis | Ratcheted upward, never shrinks | Computed once from final data |
| Cards | Phase badge, sparkline, output snippet | No phase / snippet, final stats only |
| Summary | "Leader Now / Best Avg / Fastest TTFT" with running aggregates | "Best Peak / Best Avg / Fastest TTFT" winner callouts |
| Cells table | Populates progressively, in-flight `…` markers | Final full table |
| Footer status | `LIVE` (accent) | `FROZEN` (yellow) |

## Adding a new renderer

A future web or native renderer plugs in here:

1. Consume the JSONL stream same as TUI does (use `ingest.reader`) or
   speak the v1 schema directly in your own language.
2. Build state with `domain.AppState.ingest(envelope)` (Python) or
   reimplement the same aggregation rules per the schema doc.
3. Pick a mode with `view.detect(snapshot)` (or accept a `--mode` flag).
4. Compose a ViewModel with `view.build_view_model(snap, mode)`.
5. Walk `view.layout.regions` and render each `module_id` from
   `view.modules` using your renderer's primitives.

The TUI renderer in `renderer/tui/` is a reference implementation
following exactly that pattern.

## Adding a new dashboard mode

1. Add a value to `DashboardMode` in `view/mode.py`.
2. Define a `LayoutSpec` for it in `view/layouts.py` and add to `LAYOUTS`.
3. Update `view/compose.py` if any module needs mode-specific
   parameterization.
4. Update the auto-detect rule in `view/mode.py:detect` if applicable.
5. The TUI renderer will pick it up automatically — no changes needed
   in `renderer/tui/` unless you've added a new `ModuleSpec` kind.

## Adding a new module

1. Add a `ModuleSpec` subclass in `view/modules.py` with a unique
   `kind` string.
2. Wire it into the appropriate `LayoutSpec` regions in `view/layouts.py`.
3. Add a builder in `view/compose.py` (e.g. `_my_module(snap, mode)`).
4. Add a `render_my_module(spec)` adapter in `renderer/tui/modules.py`
   and register it in the dispatch at the bottom of that file.

That's it. The domain/ingest layers don't change.
