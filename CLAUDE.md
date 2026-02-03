# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

dodgylegally is a creative audio sampling CLI tool that generates random search phrases, downloads short audio clips from YouTube (or other sources), and processes them into one-shot and looped samples. Originally a Google Colab notebook, now an installable Python CLI with a pluggable source system, metadata tracking, preset configurations, and structured logging.

Based on work by Colugo Music; public domain, no license.

## Commands

```bash
# Install (dev mode)
pip install -e .

# Run tests (302 tests)
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
│   └── builtin.py      # reverb, lowpass, highpass, bitcrush, distortion, stutter, reverse, delay
├── sources/            # Pluggable audio source system
│   ├── __init__.py     # Source registry (get_source, list_sources, weighted_select)
│   ├── base.py         # AudioSource protocol, SearchResult, DownloadedClip
│   ├── youtube.py      # YouTubeSource — yt-dlp with retry and backoff
│   └── local.py        # LocalSource — sample from local audio files
├── templates/          # Bundled YAML arrangement templates
│   ├── ambient-drift.yaml
│   ├── build-and-drop.yaml
│   ├── chaos.yaml
│   ├── rhythmic-collage.yaml
│   └── spoken-word-reveal.yaml
└── strategies/         # Arrangement and composition strategies
    ├── __init__.py     # Strategy registry
    ├── base.py         # ArrangementStrategy protocol
    ├── builtin.py      # sequential, loudness, tempo, key_compatible, layered
    └── templates.py    # YAML arrangement templates (load, apply, distribute)
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
- **Word-centered trimming** — `trim_word_centered()` centers a clip on a spoken word using whisper/caption timestamps, with zero-crossing edge snapping and micro-fades.
- **Arrangement templates** — YAML-defined section-based compositions. Five bundled: `build-and-drop`, `ambient-drift`, `chaos`, `rhythmic-collage`, `spoken-word-reveal`.

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
- `librosa` + `soundfile` — pitch/time transforms, audio analysis
- `faster-whisper` — spoken-word clip verification and word-level timestamps (assembly scripts)
- FFmpeg — runtime requirement for audio conversion

## Testing

302 tests covering CLI subcommands, clip extraction, source abstraction, local file source, metadata sidecars, weighted selection, download resilience, presets, logging, UI modes, audio processing, word-centered trimming, effects (including delay with dry/wet mix), BPM looping, transforms, strategies, templates (including spoken-word-reveal), stems, and analysis.

```bash
pytest tests/ -v
```

## Roadmap

All 4 phases complete. Design docs in `docs/plans/`:
- **Phase 1** (complete): Workflow & UX — progress, resilience, presets, logging
- **Phase 2** (complete): Source Diversity — source abstraction, local files, metadata, weighted runs
- **Phase 3** (complete): Audio Creativity — analysis, effects, BPM-aware looping, pitch/time transforms
- **Phase 4** (complete): Composition Intelligence — arrangement strategies, templates, stem export

## Standalone Scripts

Scripts in the repo root for spoken-word clip sourcing and phrase assembly:

### Clip sourcing

- `source_spoken.py` — **Unified** spoken-word sourcing script. Uses library's `transcribe_and_find()` + `trim_word_centered()` for precise centering, post-trim whisper verification, and quality gates. Outputs to `spoken_clips/<target>/tight|long/`. Replaces the per-word scripts below for new sourcing runs.
- `confetti_spoken.py` — Legacy: downloads clips where "confetti" is spoken. No midpoint fallback.
- `tornado_spoken.py` — Legacy: downloads clips for "tornado", "full of", and "tornado full of".
- `confetti_batch.py` / `confetti_sounds.py` — Earlier batch download scripts (less selective).

```bash
# Source "full of" clips (the gap)
python source_spoken.py --target "full of"

# Source with custom whisper model
python source_spoken.py --target "confetti" --whisper-model small

# Verify existing clips without downloading
python source_spoken.py --target "full of" --verify-only

# Limit to first 10 phrases
python source_spoken.py --target "tornado" --count 10
```

### Phrase assembly

- `tornado_assemble.py` — Assembles "tornado full of confetti" from spoken-word clips. Whisper-verifies every clip, scores combinations for spectral/level compatibility, splices with zero-crossing edges and crossfades.

```bash
# Scan clip inventory without assembling
python tornado_assemble.py --verify-only

# Assemble 15 versions
python tornado_assemble.py --versions 15

# Tune assembly parameters
python tornado_assemble.py --gap-ms 80 --crossfade-ms 30 --target-dbfs -16
```

Key functions (reusable outside the script):
- `verify_clip(path, target_word, model)` → `VerifiedClip | None` — whisper-confirms a word is present
- `verify_directory(dir, word, model)` → verified + rejected lists
- `extract_word(clip)` → `AudioSegment` trimmed to whisper boundaries
- `score_sequence(clips)` → float compatibility score
- `assemble_phrase(clips)` → `AudioSegment` with level-matched, crossfaded words

### Composition

- `confetti_compose.py` — Template-based compositions from confetti sample collections (cascade, wash, machine, reveal). Uses the library's template, effect, and stem systems.
- `compose_spectral_morph.py` — Sorts assembled "tornado full of confetti" versions by spectral centroid and crossfades between them. Warm-to-bright timbral shift.
- `compose_reverse_reveal.py` — Reversed wash of assembled versions with forward versions emerging at the midpoint. Dense lowpassed texture yields to clean speech.
- `compose_word_scatter.py` — Extracts individual words from assembled versions and scatters them on a rhythmic grid at 90 BPM with jitter and pitch variation.

```bash
# Run compositions (output to tornado_compositions/)
python compose_spectral_morph.py    # ~20s spectral morph
python compose_reverse_reveal.py    # ~20s reverse reveal
python compose_word_scatter.py      # ~22s word scatter
```

### Skipping rope

- `source_skipping.py` — Three-mode clip sourcing from skipping rope videos. Downloads videos and runs chant detection (whisper word-density), percussion detection (onset-dense speech-free windows), and atmosphere extraction (steady-state energy regions) on each. Outputs to `skipping_rope_clips/{chant,percussion,atmosphere}/{short,medium,long}/`.
- `skipping_assemble.py` — Profiles clips (BPM, onset density, energy variance, spectral centroid), scores within-category and cross-layer compatibility, assembles versioned mixes with gain staging.
- `skipping_compose.py` — Four compositions from skipping rope clips using multitrack infrastructure (Track, Pattern, DelayBus, mix_tracks). Playground (documentary with quarter-note delay), Rope Machine (100 BPM grid with dotted-8th delay, stutter+bitcrush), Ghost Playground (two-phase delay: sparse echoes then cascading density), Tempo Shift (80->140->80 BPM with delay times shifting per zone).

```bash
# Source clips (test with 3 phrases per category)
python source_skipping.py --category all --count 3

# Source only percussion clips
python source_skipping.py --category percussion

# Verify existing clip inventory
python source_skipping.py --verify-only

# Assemble 10 versions
python skipping_assemble.py --versions 10

# Profile clips without assembling
python skipping_assemble.py --verify-only

# Run all four compositions
python skipping_compose.py
```

Key functions (reusable outside the scripts):
- `extract_chant_regions(audio, word_timestamps)` -> list of (start, end, word_density)
- `extract_percussion_windows(audio_path, word_timestamps)` -> list of (start, end, onset_count)
- `extract_ambient_region(audio_path)` -> (start, end) or None
- `score_cross_layer(chant, perc, atmo)` -> float compatibility score
- `assemble_full_mix(chant, perc, atmo)` -> AudioSegment with gain staging

### Sample collections

```
confetti_whisper/tight/   48 × 1.0s clips (6 whisper-centered, 42 midpoint)
confetti_whisper/long/    48 × 4.0s clips (6 whisper-centered, 42 midpoint)
confetti_spoken/tight/    29 × 1.0s clips (16 whisper-verified "confetti")
confetti_spoken/long/     29 × 4.0s clips
tornado_spoken/tornado/   15 × 1.0s + 15 × 4.0s (11 verified "tornado")
tornado_spoken/full of/    6 × 1.0s +  6 × 4.0s (1 verified "full of")
tornado_spoken/tornado full of/  7 × 1.0s + 7 × 4.0s (0 verified "full of")
spoken_clips/             Word-centered clips from source_spoken.py (verified)
  tornado/                64 verified clips (super_tight 50ms/80ms/120ms + tight)
  full of/                25 verified clips (expanded from 12 via targeted phrases)
  confetti/               68 verified clips (super_tight 50ms/80ms/120ms + tight)
```

### Assembled output

```
tornado_assembled_supertight_v2/  20 assembled "tornado full of confetti" versions
  manifest.json                   Clip provenance, scores, spectral data
  v01_score2.8.wav ... v20_score19.4.wav  Scored and ranked assemblies
tornado_compositions/             Compositions built from assembled versions
  cascade_canon.wav               16-voice accelerando canon (21.3s)
  spectral_morph.wav              Warm-to-bright spectral crossfade (20.1s)
  reverse_reveal.wav              Reversed wash → forward emergence (20.0s)
  word_scatter.wav                Rhythmic word grid at 90 BPM (22.3s)
```

```
skipping_rope_clips/              Three-mode extraction output
  chant/{short,medium,long}/      Rhythmic chanting clips (2s/4s/8s)
  percussion/{short,medium,long}/ Percussive rope/feet clips (0.5s/1s/2s)
  atmosphere/{short,medium,long}/ Playground ambience clips (4s/8s/15s)
skipping_assembled/               Scored and assembled versions
  manifest.json                   Per-version score, clips, profiling data
skipping_compositions/            Four multitrack compositions with delay buses
  playground.wav                  Documentary with quarter-note delay (~30s)
  rope_machine.wav                Mechanical 100 BPM, dotted-8th delay (~21s)
  ghost_playground.wav            Two-phase cascading delay (~25s)
  tempo_shift.wav                 80->140->80 BPM, delay shifts per zone (~30s)
```

See `docs/case-study-skipping-rope.md` for the full sourcing and composition story.

**"full of" gap (resolved):** Legacy scripts yielded 1 verified clip. `source_spoken.py` with targeted search phrases (idiom explainers, grammar lessons, deliberate emphasis) expanded the pool to 25 verified clips. See `docs/case-study-super-tight.md` for the full story.

## Legacy

The original notebook (`dodgylegally.ipynb`) is preserved for reference. It ran in Google Colab with Google Drive integration and NLTK for word generation.
