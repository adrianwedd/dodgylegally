# dodgylegally Enhancements — Implementation Plan

Companion to: `2026-02-01-enhancements-design.md`

## Phase 1: Workflow & UX

### Task 1.1: Add rich progress and feedback
1. Add `rich` to pyproject.toml dependencies
2. Create `src/dodgylegally/ui.py` with console wrapper, progress bar helpers, summary table renderer
3. Write tests for ui.py (test summary formatting, progress tracking state)
4. Update `cli.py` to use ui.py instead of click.echo for all output
5. Add `--verbose` and `--quiet` flags to CLI group
6. Test: run full pipeline, verify progress bars and summary tables render

### Task 1.2: Add retry logic and resilience
1. Add `tenacity` to pyproject.toml dependencies
2. Update `download.py`: wrap yt-dlp calls with retry decorator (exponential backoff, max 3 retries)
3. Add error classification: network_error → retry, rate_limit → long backoff, not_found → skip
4. Add `--delay` flag to download and run subcommands (seconds between downloads)
5. Add `--timeout` flag to download subcommand
6. Add `--dry-run` flag to download and run subcommands
7. Write tests: mock retry scenarios, verify backoff behavior, test dry-run output
8. Test: run 50+ downloads, verify rate limit handling

### Task 1.3: Add preset configuration system
1. Add `pyyaml` to pyproject.toml dependencies
2. Create `src/dodgylegally/config.py`: preset loading, merging with CLI flags, user config directory
3. Create bundled presets in `src/dodgylegally/presets/`: default.yaml, ambient.yaml, percussive.yaml, chaotic.yaml
4. Add `--preset` flag to run subcommand
5. Write tests: preset loading, merging, override behavior, missing preset error
6. Test: run with each built-in preset

### Task 1.4: Add structured logging
1. Create `src/dodgylegally/logging_config.py`: configure Python logging, formatters, handlers
2. Add `--log-file` flag to CLI group
3. Replace remaining print/click.echo calls with logging calls across all modules
4. Write tests: verify log output format, log file creation
5. Test: run pipeline with --log-file, inspect output

---

## Phase 2: Source Diversity

### Task 2.1: Create source abstraction layer
1. Create `src/dodgylegally/sources/` package
2. Create `sources/base.py`: AudioSource protocol, SearchResult and DownloadedClip dataclasses
3. Create `sources/youtube.py`: extract existing download.py logic into YouTubeSource class
4. Create `sources/__init__.py`: source registry (get_source by name)
5. Update `download.py` to delegate to source registry (backward compatible)
6. Update `cli.py`: add `--source` flag to download and run subcommands
7. Write tests: source registry, YouTubeSource (adapts existing download tests)
8. Test: existing pipeline still works identically via YouTubeSource

### Task 2.2: Add Freesound integration
1. Create `sources/freesound.py`: FreesoundSource implementing AudioSource protocol
2. Implement API key management in config.py (read from ~/.config/dodgylegally/config.yaml)
3. Implement search (text query, duration filter, license filter)
4. Implement download (fetch audio, convert to WAV, extract clip)
5. Respect rate limits (60 req/min)
6. Write tests: mock Freesound API responses, test search/download flow
7. Register FreesoundSource in source registry
8. Test: search and download from Freesound with real API key

### Task 2.3: Add local file source
1. Create `sources/local.py`: LocalSource implementing AudioSource protocol
2. Implement search (glob pattern matching on local directories)
3. Implement download (copy + extract 1-second clip from random position)
4. Support WAV, MP3, FLAC, OGG, AIFF
5. Add `--local-path` flag to download subcommand
6. Write tests: test with temp directory of audio files
7. Test: run pipeline with local files as source

### Task 2.4: Add metadata sidecar system
1. Create `src/dodgylegally/metadata.py`: read/write JSON sidecars, merge metadata
2. Update sources to write metadata on download
3. Update process.py to read and extend metadata (add processing params)
4. Update combine.py to read and aggregate metadata
5. Write tests: metadata creation, reading, merging, pipeline propagation
6. Test: run pipeline, verify .json sidecars exist alongside every .wav

### Task 2.5: Add multi-source weighted runs
1. Update cli.py run subcommand: parse `--source youtube:7 --source freesound:3`
2. Implement weighted source selection in sources/__init__.py
3. Update run pipeline to pull from multiple sources
4. Add source weights to preset YAML format
5. Write tests: weighted selection distribution, preset source config
6. Test: run with mixed sources, verify distribution

---

## Phase 3: Audio Creativity

### Task 3.1: Add audio analysis module
1. Add `librosa` and `soundfile` to pyproject.toml dependencies
2. Create `src/dodgylegally/analyze.py`: AudioAnalysis dataclass, analyze_file function
3. Implement BPM detection (librosa.beat.beat_track)
4. Implement key detection (librosa.feature.chroma, estimate key from chroma)
5. Implement loudness measurement (LUFS calculation)
6. Implement spectral analysis (centroid, RMS, zero-crossing rate)
7. Add analysis caching (store in metadata sidecar, skip if file unchanged)
8. Add `analyze` subcommand to cli.py
9. Write tests: analyze known audio files, verify BPM/key/loudness ranges
10. Test: analyze case study samples, verify reasonable results

### Task 3.2: Build effects system
1. Create `src/dodgylegally/effects/` package
2. Create `effects/base.py`: AudioEffect protocol, EffectChain class
3. Implement effects: reverb, delay, filter (lowpass/highpass/bandpass), bitcrush, distortion, reverse, stutter
4. Create `effects/__init__.py`: effect registry, chain parser (parse "reverb:0.5,lowpass:3000")
5. Add `--effects` flag to process subcommand
6. Add effects configuration to preset YAML format
7. Write tests: each effect individually, chain composition, CLI parsing
8. Test: process samples with various effect chains, listen to output

### Task 3.3: Add BPM-aware looping
1. Update process.py loop generation: use BPM from analysis to calculate beat-aligned loop length
2. Add `--target-bpm` flag to process subcommand
3. Implement time-stretching to target BPM (librosa.effects.time_stretch)
4. Implement zero-crossing alignment for click-free loops
5. Fall back to current fixed-length behavior when BPM detection fails
6. Write tests: BPM-aligned loop length calculation, time-stretch, fallback behavior
7. Test: process samples with --target-bpm 120, verify loops are beat-aligned

### Task 3.4: Add pitch and time transforms
1. Create `src/dodgylegally/transform.py`: time_stretch, pitch_shift, key_match functions
2. Add `--stretch`, `--pitch`, `--target-key` flags to process subcommand
3. Implement time-stretch (librosa.effects.time_stretch)
4. Implement pitch-shift (librosa.effects.pitch_shift)
5. Implement key-match (analyze current key, calculate shift interval, apply pitch-shift)
6. Write tests: time-stretch ratios, pitch-shift intervals, key matching logic
7. Test: process samples with various transforms, verify output

---

## Phase 4: Composition Intelligence

### Task 4.1: Implement arrangement strategies
1. Create `src/dodgylegally/strategies/` package
2. Create `strategies/base.py`: ArrangementStrategy protocol
3. Implement strategies: sequential (current), loudness, tempo, key_compatible, random_weighted, layered
4. Create `strategies/__init__.py`: strategy registry
5. Refactor combine.py to use strategy protocol (current behavior = sequential strategy)
6. Add `--strategy` flag to combine subcommand
7. Write tests: each strategy with mock audio data, strategy registry
8. Test: combine samples with each strategy, listen to output

### Task 4.2: Add arrangement templates
1. Create bundled template YAML files in `src/dodgylegally/templates/`
2. Create `strategies/templates.py`: template parser, section-based arrangement
3. Add `--template` flag to combine subcommand
4. Build templates: build-and-drop, ambient-drift, rhythmic-collage, chaos
5. Write tests: template parsing, section duration calculation, strategy delegation
6. Test: combine with each template, verify section transitions

### Task 4.3: Add multi-track stem export
1. Update combine.py: add stem export mode
2. Add `--stems` flag to combine subcommand
3. Generate individual stem files alongside full mix
4. Generate manifest.json with track listing, timing, and metadata
5. Write tests: stem file creation, manifest accuracy, timing alignment
6. Test: export stems, import into a DAW, verify alignment

---

## Issue Dependency Graph

```
Phase 1 (no dependencies):
  1.1 Progress → 1.2 Resilience → 1.3 Presets → 1.4 Logging
  (1.1 and 1.4 can run in parallel; 1.3 depends on 1.1 for UI)

Phase 2 (depends on Phase 1 for presets and resilience):
  2.1 Source abstraction (required by all Phase 2)
  2.2 Freesound ──┐
  2.3 Local files ──┼── 2.4 Metadata ── 2.5 Multi-source
  (2.1 required first; 2.2, 2.3 parallel; 2.4 after any source; 2.5 last)

Phase 3 (depends on Phase 2 for metadata):
  3.1 Analysis (required by 3.3, 3.4)
  3.2 Effects (independent)
  3.3 BPM looping (depends on 3.1)
  3.4 Pitch/time (depends on 3.1)
  (3.1 and 3.2 parallel; 3.3 and 3.4 parallel after 3.1)

Phase 4 (depends on Phase 3 for analysis):
  4.1 Strategies (required by 4.2)
  4.2 Templates (depends on 4.1)
  4.3 Stems (independent, can parallel with 4.1)
```
