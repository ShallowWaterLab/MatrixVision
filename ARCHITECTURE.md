# MatrixVision Architecture

## Overview

MatrixVision is a terminal Matrix-rain experience driven by live camera input.
The brighter a region of the captured frame, the more likely/denser the rain becomes there.
Goal: one command launch, responsive terminal UI, stable FPS.

## Core Modules

### 1. Camera Manager
- Enumerates `/dev/video*` via OpenCV `VideoCapture`.
- Opens selected device with requested resolution/FPS.
- Streams frames into the visualization loop.

### 2. Capture Pipeline
- `cap.read()` grabs frames.
- Resize to terminal grid size (`cols x rows`).
- Convert to grayscale.
- Compute per-column brightness energy for rain modulation.

### 3. Rain Engine
- Per-column float heads with individual speed offset (`0.6x..1.4x`).
- Brightness-driven energy:
  - higher energy = longer trail, faster fall, denser spawn.
- Charsets:
  - mix: ASCII + half-width katakana
  - ascii: ASCII only
  - kana: katakana only
- Dirty-rectangle rendering:
  - only changed cells are rewritten to reduce flicker.

### 4. Terminal I/O
- Raw ANSI output with cursor hide, screen clear, cursor-position writes.
- Non-blocking stdin read for controls.

## Controls

- `Q` / `Ctrl+C` / `Esc`: quit
- `Space`: pause / resume
- `K`: cycle charset `mix -> ascii -> kana`

## Startup

```bash
MatrixVision
MatrixVision <camera_index> <width> <height>
```

## Reproducibility
- Verified with OpenCV `5.0.0` on Linux.
- Requires terminal that supports ANSI true-color and UTF-8.

## Milestones
- [x] Architecture doc
- [x] Camera discovery + capture
- [x] Matrix rain with brightness modulation
- [x] Charset switching and pause/resume
- [ ] Screenshot save from terminal frame
- [ ] Audio-reactive energy mode
- [ ] Recording to GIF/MP4
