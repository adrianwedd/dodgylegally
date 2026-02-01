# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

dodgylegally is a creative audio sampling CLI tool that generates random search phrases, downloads short audio clips from YouTube (or other sources), and processes them into one-shot and looped samples. Originally a Google Colab notebook, now an installable Python CLI with a pluggable source system, metadata tracking, preset configurations, and structured logging.

Based on work by Colugo Music; public domain, no license.

## Commands

```bash
# Install (dev mode)
pip install -e .

# Run tests (101 tests)
pytest tests/ -v

# CLI usage
dodgylegally --help
dodgylegally search --count 5
dodgylegally download --phrase "rain thunder" --source youtube
dodgylegally download --phrase "ambient pad" --source local
dodgylegally process
dodgylegally combine
dodgylegally run --count 10 -o ./my_samples
dodgylegally run --count 20 --preset ambient --dry-run
dodgylegally run --count 10 --source youtube:7 --source local:3
```

Requires FFmpeg installed for audio processing (`brew install ffmpeg` on macOS).

## Architecture

```
src/dodgylegally/
├── cli.py              # Click CLI entry point with subcommands
├── search.py           # Word list loading and random phrase generation
├── download.py         # Legacy yt-dlp wrapper (download_url for direct URLs)
├── process.py          # One-shot and loop audio processing (pydub)
├── combine.py          # Versioned loop merging
├── config.py           # YAML preset loading and merging
├── metadata.py         # JSON sidecar read/write/merge for sample provenance
├── ui.py               # Console output wrapper (quiet/verbose/debug modes)
├── logging_config.py   # Python logging configuration
├── wordlist.txt        # Bundled 5000-word list
├── presets/            # Bundled YAML presets (default, ambient, percussive, chaotic)
└── sources/            # Pluggable audio source system
    ├── __init__.py     # Source registry (get_source, list_sources, weighted_select)
    ├── base.py         # AudioSource protocol, SearchResult, DownloadedClip
    ├── youtube.py      # YouTubeSource — yt-dlp with retry and backoff
    └── local.py        # LocalSource — sample from local audio files
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

### Subcommands

- **search** — Generates random 2-word phrases from bundled or custom word list, outputs to stdout
- **download** — Downloads audio clips via pluggable sources (`--source youtube|local`). Supports `--delay`, `--dry-run`, `--url` for direct downloads.
- **process** — Creates one-shot (capped 2000ms, fade-out) and loop (cross-fade, overlay) variants
- **combine** — Concatenates loops (repeated N times per `--repeats`) into versioned combined file
- **run** — Full pipeline end-to-end. Supports `--preset`, `--source` (repeatable with weights), `--delay`, `--dry-run`.

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
└── combined/     # Combined loop files (versioned)
```

## Dependencies

- `click` — CLI framework
- `pydub` — audio processing
- `pyyaml` — preset configuration
- `yt-dlp` — YouTube downloading
- FFmpeg — runtime requirement for audio conversion

## Testing

101 tests across 14 test files covering CLI subcommands, source abstraction, local file source, metadata sidecars, weighted selection, download resilience, presets, logging, UI modes, and audio processing.

```bash
pytest tests/ -v
```

## Roadmap

Active development across 4 phases. Design docs in `docs/plans/`:
- **Phase 1** (complete): Workflow & UX — progress, resilience, presets, logging
- **Phase 2** (complete): Source Diversity — source abstraction, local files, metadata, weighted runs
- **Phase 3** (next): Audio Creativity — analysis, effects, BPM-aware looping, pitch/time transforms
- **Phase 4** (planned): Composition Intelligence — arrangement strategies, templates, stem export

## Legacy

The original notebook (`dodgylegally.ipynb`) is preserved for reference. It ran in Google Colab with Google Drive integration and NLTK for word generation.
