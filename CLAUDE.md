# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

dodgylegally is a creative audio sampling CLI tool that generates random search phrases, downloads short audio clips from YouTube (or other sources), and processes them into one-shot and looped samples. Originally a Google Colab notebook, now an installable Python CLI with a pluggable source system, metadata tracking, preset configurations, and structured logging.

Based on work by Colugo Music; public domain, no license.

## Commands

```bash
# Install (dev mode)
pip install -e .

# Run tests (222 tests)
pytest tests/ -v

# CLI usage
dodgylegally --help
dodgylegally search --count 5
dodgylegally download --phrase "rain thunder" --source youtube
dodgylegally download --phrase "ambient pad" --source local
dodgylegally download --phrase "rain" --clip-position random --clip-duration 2.0
dodgylegally download --phrase "rain" --clip-position 15.0 --clip-duration 3.0
dodgylegally process
dodgylegally combine
dodgylegally run --count 10 -o ./my_samples
dodgylegally run --count 20 --preset ambient --dry-run
dodgylegally run --count 10 --source youtube:7 --source local:3
dodgylegally run --count 5 --clip-position random --clip-duration 2.0
```

Requires FFmpeg installed for audio processing (`brew install ffmpeg` on macOS).

## Architecture

```
src/dodgylegally/
├── cli.py              # Click CLI entry point with subcommands
├── clip.py             # ClipSpec, ClipPosition, DownloadRangeFunc — clip extraction config
├── search.py           # Word list loading and random phrase generation
├── download.py         # Legacy yt-dlp wrapper (download_url for direct URLs)
├── process.py          # One-shot and loop audio processing (pydub)
├── combine.py          # Versioned loop merging
├── config.py           # YAML preset loading and merging
├── metadata.py         # JSON sidecar read/write/merge for sample provenance
├── analyze.py          # Audio analysis — BPM, key, loudness, spectral features
├── looping.py          # BPM-aware loop creation, beat alignment, zero-crossing
├── transform.py        # Pitch shifting, time stretching, key matching
├── stems.py            # Stem export alongside full mix
├── ui.py               # Console output wrapper (quiet/verbose/debug modes)
├── logging_config.py   # Python logging configuration
├── wordlist.txt        # Bundled 5000-word list
├── presets/            # Bundled YAML presets (default, ambient, percussive, chaotic)
├── effects/            # Pluggable audio effect system
│   ├── __init__.py     # Effect registry, parse_chain
│   ├── base.py         # AudioEffect protocol
│   └── builtin.py      # reverb, lowpass, highpass, bitcrush, distortion, stutter, reverse
├── sources/            # Pluggable audio source system
│   ├── __init__.py     # Source registry (get_source, list_sources, weighted_select)
│   ├── base.py         # AudioSource protocol, SearchResult, DownloadedClip
│   ├── youtube.py      # YouTubeSource — yt-dlp with retry and backoff
│   └── local.py        # LocalSource — sample from local audio files
└── strategies/         # Arrangement and composition strategies
    ├── __init__.py     # Strategy registry
    ├── base.py         # ArrangementStrategy protocol
    ├── builtin.py      # sequential, loudness, tempo, key_compatible, layered
    └── templates.py    # YAML arrangement templates (build-and-drop, ambient-drift)
```

**Pipeline:** search → download → process → combine

Each module exposes plain Python functions. The CLI is a thin arg-parsing layer. All inter-step communication happens via the filesystem through a shared `--output` directory. Every sample carries a `.json` metadata sidecar for provenance tracking.

### Key Design Patterns

- **Protocol-based sources** — `AudioSource` is a `typing.Protocol`. Add new sources without touching existing code.
- **Source registry** — `get_source("youtube")` returns an instance. `register_source("name", Class)` to add.
- **Weighted selection** — `--source youtube:7 --source local:3` for probabilistic multi-source runs.
- **Sidecar metadata** — `.json` companion files alongside every `.wav` tracking source, query, timestamps.
- **Preset system** — YAML presets in bundled dir or `~/.config/dodgylegally/presets/`. CLI flags override.
- **Mutually exclusive options** — `--verbose` and `--quiet` enforced via custom `_MutuallyExclusiveOption`.
- **Configurable clip extraction** — `ClipSpec` dataclass controls position (midpoint/random/timestamp) and duration; shared by all sources and the legacy download module.

### Subcommands

- **search** — Generates random 2-word phrases from bundled or custom word list, outputs to stdout
- **download** — Downloads audio clips via pluggable sources (`--source youtube|local`). Supports `--delay`, `--dry-run`, `--url` for direct downloads, `--clip-position` (midpoint/random/timestamp), `--clip-duration`.
- **process** — Creates one-shot (capped 2000ms, fade-out) and loop (cross-fade, overlay) variants. Supports `--effects`, `--target-bpm`, `--stretch`, `--pitch`, `--target-key`.
- **combine** — Concatenates loops (repeated N times per `--repeats`) into versioned combined file. Supports `--strategy`, `--template`, `--stems`.
- **analyze** — BPM, key, loudness, and spectral analysis of audio files. Supports `--no-cache`.
- **run** — Full pipeline end-to-end. Supports `--preset`, `--source` (repeatable with weights), `--delay`, `--dry-run`, `--clip-position`, `--clip-duration`.

Subcommands compose via piping: `dodgylegally search --count 5 | dodgylegally download --phrases-file -`

### Global Flags

- `--output` / `-o` — Output directory (default: `./dodgylegally_output`)
- `--verbose` / `-v` — Show debug output
- `--quiet` / `-q` — Suppress all output except errors
- `--log-file` — Write structured log to file

## Output Directory Layout

```
<output>/
├── raw/          # Downloaded audio clips + JSON metadata sidecars
├── oneshot/      # One-shot processed samples
├── loop/         # Loop processed samples
├── combined/     # Combined loop files (versioned)
└── stems/        # Individual stem files + manifest (when --stems used)
```

## Dependencies

- `click` — CLI framework
- `pydub` — audio processing
- `pyyaml` — preset configuration
- `yt-dlp` — YouTube downloading
- FFmpeg — runtime requirement for audio conversion

## Testing

222 tests across 22 test files covering CLI subcommands, clip extraction, source abstraction, local file source, metadata sidecars, weighted selection, download resilience, presets, logging, UI modes, audio processing, effects, BPM looping, transforms, strategies, templates, stems, and analysis.

```bash
pytest tests/ -v
```

## Roadmap

All 4 phases complete. Design docs in `docs/plans/`:
- **Phase 1** (complete): Workflow & UX — progress, resilience, presets, logging
- **Phase 2** (complete): Source Diversity — source abstraction, local files, metadata, weighted runs
- **Phase 3** (complete): Audio Creativity — analysis, effects, BPM-aware looping, pitch/time transforms
- **Phase 4** (complete): Composition Intelligence — arrangement strategies, templates, stem export

## Legacy

The original notebook (`dodgylegally.ipynb`) is preserved for reference. It ran in Google Colab with Google Drive integration and NLTK for word generation.
