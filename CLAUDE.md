# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

dodgylegally is a creative audio sampling CLI tool that generates random search phrases, downloads short audio clips from YouTube, and processes them into one-shot and looped samples. Originally a Google Colab notebook, now an installable Python CLI.

Based on work by Colugo Music; public domain, no license.

## Commands

```bash
# Install (dev mode)
pip install -e .

# Run tests
pytest tests/ -v

# CLI usage
dodgylegally --help
dodgylegally search --count 5
dodgylegally download --phrase "rain thunder"
dodgylegally process
dodgylegally combine
dodgylegally run --count 10 -o ./my_samples
```

Requires FFmpeg installed for audio processing (`brew install ffmpeg` on macOS).

## Architecture

```
src/dodgylegally/
├── cli.py          # Click CLI entry point with subcommands
├── search.py       # Word list loading and random phrase generation
├── download.py     # yt-dlp wrapper for YouTube audio download
├── process.py      # One-shot and loop audio processing (pydub)
├── combine.py      # Versioned loop merging
└── wordlist.txt    # Bundled 5000-word list
```

**Pipeline:** search → download → process → combine

Each module exposes plain Python functions. The CLI is a thin arg-parsing layer. All inter-step communication happens via the filesystem through a shared `--output` directory.

### Subcommands

- **search** — Generates random 2-word phrases from bundled or custom word list, outputs to stdout
- **download** — Downloads 1-second audio clips from YouTube video midpoints via yt-dlp
- **process** — Creates one-shot (capped 2000ms, fade-out) and loop (cross-fade, overlay) variants
- **combine** — Concatenates loops (repeated 3-4x each) into versioned combined file
- **run** — Full pipeline end-to-end

Subcommands compose via piping: `dodgylegally search --count 5 | dodgylegally download --phrases-file -`

## Output Directory Layout

```
<output>/
├── raw/          # Downloaded audio clips
├── oneshot/      # One-shot processed samples
├── loop/         # Loop processed samples
└── combined/     # Combined loop files (versioned)
```

## Dependencies

- `click` — CLI framework
- `pydub` — audio processing
- `yt-dlp` — YouTube downloading
- FFmpeg — runtime requirement for audio conversion

## Legacy

The original notebook (`dodgylegally.ipynb`) is preserved for reference. It ran in Google Colab with Google Drive integration and NLTK for word generation.
