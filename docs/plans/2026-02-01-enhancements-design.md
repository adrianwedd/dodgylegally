# dodgylegally Enhancements — Solution Design

## Overview

Four phases of enhancements that build on each other: harden the pipeline, diversify sources, add audio intelligence, then compose smarter.

## Architecture Principles

- **Same CLI shape** — New features are flags and subcommands, not a different tool.
- **Sidecar metadata** — Every sample gets a `.json` sidecar tracking source, analysis, and processing history.
- **Protocol-based extension** — Sources and effects use Python protocols. Add a new source or effect without touching existing code.
- **Presets over flags** — Complex configurations live in YAML presets. CLI flags for one-off overrides.

---

## Phase 1: Workflow & UX

Harden the existing pipeline. Make it reliable enough to run 100+ samples unattended.

### 1.1 Progress & Feedback

Add `rich` as a dependency. Replace click.echo with rich console for:
- Progress bars on download, process, combine steps
- Summary tables after each step (downloaded: 8, failed: 2, skipped: 1)
- `--verbose` flag for debug output, `--quiet` for silent operation

**Files:** `cli.py` (replace echo calls), new `ui.py` module for rich wrappers.

### 1.2 Resilience

Rate limiting is the primary failure mode (documented in the tornado case study: HTTP 403 after ~50 rapid requests).

- Exponential backoff with jitter on download failures (tenacity library)
- Configurable delay between downloads: `--delay 2` (seconds)
- Retry classification: network errors → retry, "no results" → skip, rate limit → backoff
- `--dry-run` flag: show what would be searched/downloaded without doing it
- Download timeout: `--timeout 30` (seconds per video)

**Files:** `download.py` (retry logic), `cli.py` (new flags).

### 1.3 Configuration & Presets

YAML preset files for repeatable configurations:

```yaml
# presets/ambient.yaml
count: 20
delay: 3
effects:
  - reverb: {room_size: 0.8}
  - lowpass: {freq: 4000}
combine:
  order: loudness
  repeats: 4-6
```

- `--preset ambient` flag on `run` command
- Built-in presets: `default`, `ambient`, `percussive`, `chaotic`
- User presets in `~/.config/dodgylegally/presets/`
- CLI flags override preset values

**Files:** new `config.py` module, bundled preset YAML files, `cli.py` (--preset flag).

### 1.4 Logging

Replace ad-hoc print/click.echo with Python logging:
- Structured log output (timestamp, level, module)
- `--log-file` flag for persistent logs
- Log download URLs, processing parameters, errors with context

**Files:** new `logging_config.py`, updates across all modules.

---

## Phase 2: Source Diversity

Abstract audio sources so YouTube is one option among many.

### 2.1 Source Protocol

```python
class AudioSource(Protocol):
    name: str

    def search(self, query: str, max_results: int = 1) -> list[SearchResult]:
        ...

    def download(self, result: SearchResult, output_dir: Path) -> DownloadedClip:
        ...

@dataclass
class SearchResult:
    source: str        # "youtube", "freesound", "local"
    title: str
    url: str
    duration_s: float | None
    metadata: dict

@dataclass
class DownloadedClip:
    path: Path
    source_result: SearchResult
    duration_ms: int
```

Refactor `download.py` → `sources/youtube.py` implementing this protocol.

**Files:** new `sources/` package with `__init__.py`, `base.py`, `youtube.py`.

### 2.2 Freesound Integration

[Freesound.org](https://freesound.org) has 500k+ Creative Commons sounds with a REST API.

- API key stored in `~/.config/dodgylegally/config.yaml`
- Search by text query (same phrases the search module generates)
- Filter by duration (0.5s–5s), license, file type
- Download, convert to WAV, extract 1-second clip
- Respect API rate limits (60 requests/minute)

**Files:** `sources/freesound.py`, `config.py` (API key management).

### 2.3 Local File Ingestion

Use local audio files as a source:

```bash
dodgylegally download --source local --local-path ~/Music/field-recordings/
```

- Glob pattern matching for input files
- Random selection from matching files
- Extract 1-second clip from random position (not just midpoint)
- Supports WAV, MP3, FLAC, OGG, AIFF

**Files:** `sources/local.py`.

### 2.4 Source Metadata (Sidecar Files)

Every downloaded clip gets a JSON sidecar:

```json
{
  "source": "youtube",
  "query": "goshen duress",
  "url": "https://youtube.com/watch?v=3Fr0nq9JJbM",
  "title": "Goshen - Duress (Official Audio)",
  "downloaded_at": "2026-02-01T14:30:00Z",
  "clip_start_ms": 45000,
  "clip_duration_ms": 1000,
  "license": "unknown"
}
```

Metadata follows the sample through processing (process and combine steps update it).

**Files:** new `metadata.py` module, updates to `process.py` and `combine.py`.

### 2.5 Multi-Source Runs

The `run` command supports multiple sources with weighting:

```bash
dodgylegally run --count 10 --source youtube:7 --source freesound:3
```

This generates 10 samples: ~7 from YouTube, ~3 from Freesound. Presets can configure source weights.

**Files:** `cli.py` (--source flag), `sources/__init__.py` (source registry, weighted selection).

---

## Phase 3: Audio Creativity

Analyze audio properties and apply effects. This is where samples become instruments.

### 3.1 Audio Analysis

New `analyze.py` module using `librosa`:

```python
@dataclass
class AudioAnalysis:
    bpm: float | None
    key: str | None          # e.g., "C minor"
    loudness_lufs: float
    duration_ms: int
    spectral_centroid: float  # brightness measure
    rms_energy: float
    zero_crossing_rate: float
```

- `dodgylegally analyze` subcommand: analyze all samples in a directory
- Analysis results written to JSON sidecar (extends metadata from Phase 2)
- Analysis cache: skip re-analysis if file unchanged

**Files:** new `analyze.py`, `cli.py` (analyze subcommand).

**New dependency:** `librosa` (pulls in numpy, scipy — significant but standard for audio work).

### 3.2 Effects System

Composable effects chain with a protocol:

```python
class AudioEffect(Protocol):
    name: str

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        ...
```

Built-in effects:
- **Reverb** — Convolution with impulse response (or simple algorithmic)
- **Delay** — Echo with feedback and decay
- **Filter** — Lowpass, highpass, bandpass with configurable frequency
- **Bitcrush** — Reduce bit depth for lo-fi character
- **Distortion** — Soft/hard clipping
- **Chorus** — Modulated delay for width
- **Reverse** — Play sample backwards
- **Stutter** — Repeat micro-segments for glitch effects

CLI usage:

```bash
dodgylegally process --effects "reverb:0.5,lowpass:3000,bitcrush:8"
```

Presets can define effect chains.

**Files:** new `effects/` package with `__init__.py`, `base.py`, and one file per effect.

### 3.3 BPM-Aware Looping

Current loops are fixed at 1 second. BPM-aware looping:

- Detect BPM of source audio (from analysis)
- Calculate loop length that aligns with beat boundaries
- Time-stretch loop to target BPM if `--target-bpm` specified
- Quantize loop start/end to zero crossings for click-free loops

```bash
dodgylegally process --target-bpm 120
```

**Files:** `process.py` (loop logic update), `analyze.py` (BPM detection).

### 3.4 Pitch & Time

- **Time-stretch** — Change tempo without pitch: `--stretch 1.5` (150% speed)
- **Pitch-shift** — Change pitch without tempo: `--pitch +3` (semitones)
- **Key-match** — Shift all samples to a target key: `--target-key "C minor"`

Uses librosa's time-stretch and pitch-shift algorithms.

**Files:** new `transform.py` module, `cli.py` (new flags on process subcommand).

---

## Phase 4: Composition Intelligence

Make `combine` smarter. Turn a pile of random samples into something musical.

### 4.1 Arrangement Strategies

Replace the simple "concatenate with random repeats" with pluggable strategies:

- **Sequential** (current) — Concatenate in file order, each repeated N times
- **Loudness** — Order by LUFS (quiet → loud for builds, loud → quiet for ambient)
- **Tempo** — Group by similar BPM, time-stretch outliers to match
- **Key-compatible** — Group samples with harmonically compatible keys
- **Random-weighted** — Weight selection by audio properties (bright samples more likely in "chorus" section)
- **Layered** — Overlay 2-3 samples at a time instead of sequential concatenation

```bash
dodgylegally combine --strategy loudness
dodgylegally combine --strategy layered --max-layers 3
```

**Files:** new `strategies/` package, `combine.py` (refactor to use strategies), `cli.py` (--strategy flag).

### 4.2 Arrangement Templates

Pre-defined structures that use strategies:

```yaml
# templates/build-and-drop.yaml
sections:
  - name: intro
    strategy: loudness
    direction: ascending
    duration_s: 8
  - name: drop
    strategy: layered
    max_layers: 4
    duration_s: 4
  - name: outro
    strategy: loudness
    direction: descending
    duration_s: 8
```

```bash
dodgylegally combine --template build-and-drop
```

**Files:** bundled template YAML files, `strategies/templates.py`.

### 4.3 Multi-Track Export

Export as separate stems instead of a single mixed file:

```bash
dodgylegally combine --stems
```

Creates:
```
combined/
├── combined_v1.wav           # Full mix
├── combined_v1_stem_01.wav   # Individual tracks
├── combined_v1_stem_02.wav
└── combined_v1_manifest.json # Track listing with timing
```

The manifest JSON enables import into DAWs or further programmatic arrangement.

**Files:** `combine.py` (stem export), manifest generation.

---

## New Dependencies

| Package | Phase | Purpose |
|---------|-------|---------|
| `rich` | 1 | Progress bars, tables, pretty output |
| `tenacity` | 1 | Retry logic with backoff |
| `pyyaml` | 1 | Preset/config file parsing |
| `librosa` | 3 | Audio analysis (BPM, key, spectral) |
| `soundfile` | 3 | Better audio I/O for librosa |

## New Modules

| Module | Phase | Purpose |
|--------|-------|---------|
| `ui.py` | 1 | Rich console wrappers |
| `config.py` | 1 | Preset loading, user config |
| `sources/` | 2 | Audio source protocol and implementations |
| `metadata.py` | 2 | JSON sidecar read/write |
| `analyze.py` | 3 | Audio analysis (BPM, key, loudness) |
| `effects/` | 3 | Effect protocol and implementations |
| `transform.py` | 3 | Time-stretch, pitch-shift |
| `strategies/` | 4 | Arrangement strategy protocol and implementations |

## CLI Changes Summary

New subcommands:
- `dodgylegally analyze` — Analyze samples in a directory

New flags on existing subcommands:
- `run`: `--preset`, `--source`, `--delay`, `--dry-run`, `--verbose`, `--quiet`
- `download`: `--source`, `--delay`, `--timeout`, `--dry-run`
- `process`: `--effects`, `--target-bpm`, `--target-key`, `--stretch`, `--pitch`
- `combine`: `--strategy`, `--template`, `--stems`, `--target-bpm`
