# dodgylegally

You type a number. The machine picks two words at random — *spinelet digeny*, *goshen duress*, *befit zygote* — searches YouTube for each absurd phrase, grabs one second of audio from the middle of whatever it finds, and hands you back a sample you never could have imagined.

Do it ten times and you have a sample pack. Do it a hundred times and you have an instrument.

**dodgylegally** is a CLI tool for generating audio samples from the chaos of YouTube — and beyond. It searches, downloads, processes, and combines, turning random words into one-shots, loops, and compositions. Pull from YouTube, sample your own library, mix sources with weighted randomness, and track every sample back to its origin.

---

## How it works

```
words ──→ phrases ──→ sources ──→ audio ──→ samples
```

1. **Search** — Pairs random words from a 5,000-word dictionary into phrases no human would type.
2. **Download** — Searches audio sources for each phrase. Extracts a short clip from each result. Retries on failure, backs off on rate limits.
3. **Process** — Shapes each clip into two variants: a **one-shot** (2s max, normalized, fade-out) and a **loop** (1s, cross-faded for seamless repeat).
4. **Combine** — Stitches all loops together, each repeated 3-4 times, into a single versioned file.

Every run produces different output. Two people running the same command will get completely different audio. Every sample gets a JSON sidecar tracking where it came from.

## Quick start

```bash
pip install .
dodgylegally run --count 10
```

That's it. Ten random samples, downloaded, processed, and combined. Output lands in `./dodgylegally_output/`.

### Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/)

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

## Usage

### The full pipeline

```bash
# 10 random samples from YouTube
dodgylegally run --count 10

# Custom output directory
dodgylegally run --count 5 -o ~/Music/samples

# Use a themed word list
dodgylegally run --count 20 --wordlist weather_words.txt

# Use a preset
dodgylegally run --count 20 --preset ambient

# Mix sources: ~70% YouTube, ~30% local files
dodgylegally run --count 10 --source youtube:7 --source local:3

# Preview what would happen without downloading
dodgylegally run --count 10 --dry-run

# Verbose output for debugging
dodgylegally run --count 5 -v

# Quiet mode — errors only
dodgylegally run --count 50 -q

# Log everything to a file
dodgylegally run --count 50 --log-file run.log
```

### Step by step

Each stage of the pipeline is a separate subcommand. Run them individually for more control.

```bash
# Generate random search phrases
dodgylegally search --count 5
# → "merchet missal"
# → "streyne string"
# → "goracco elysia"
# → "outreach kelpware"
# → "zagged undrossy"

# Download audio for specific phrases
dodgylegally download --phrase "rain thunder"
dodgylegally download --phrase "ocean waves" --phrase "wind chimes"

# Download from a direct YouTube URL
dodgylegally download --url "https://youtube.com/watch?v=..."

# Download with rate limit protection
dodgylegally download --phrase "wind" --delay 2.0

# Download from local audio files instead of YouTube
dodgylegally download --phrase "ambient" --source local

# Process raw downloads into one-shots and loops
dodgylegally process

# Combine loops into a single file
dodgylegally combine

# Custom repeat range for combine (default: 3-4)
dodgylegally combine --repeats 2-6
```

### Piping

Subcommands compose through stdin. Generate phrases, pipe them into download, then process and combine:

```bash
dodgylegally search --count 20 | dodgylegally download --phrases-file -
dodgylegally process
dodgylegally combine
```

### Presets

Bundled presets for common workflows:

| Preset | Count | Delay | Repeats | Character |
|--------|-------|-------|---------|-----------|
| `default` | 10 | 0s | 3-4 | Balanced starting point |
| `ambient` | 20 | 3s | 4-6 | Slow, patient, textural |
| `percussive` | 15 | 2s | 2-3 | Punchy, rhythmic |
| `chaotic` | 50 | 1s | 1-2 | Fast, dense, unpredictable |

```bash
dodgylegally run --count 20 --preset ambient
```

Custom presets go in `~/.config/dodgylegally/presets/` as YAML files. CLI flags override preset values.

### Custom word lists

The built-in dictionary has 5,000 words. For themed collections, supply your own:

```bash
echo -e "rain\nthunder\nstorm\nlightning\ndrizzle\nhail" > weather.txt
dodgylegally run --count 10 --wordlist weather.txt
```

The phrases will still be random pairs (*thunder drizzle*, *hail storm*), but the source material will skew toward weather-related videos.

### Audio sources

dodgylegally has a pluggable source system. Each source implements the same protocol — search, download, done.

| Source | Description |
|--------|-------------|
| `youtube` (default) | Searches YouTube via yt-dlp. Extracts a 1-second clip from the video midpoint. |
| `local` | Scans a local directory for audio files (WAV, MP3, FLAC, OGG, AIFF). Extracts a 1-second clip from a random position. |

Sources can be weighted for mixed runs:

```bash
# ~70% YouTube, ~30% local
dodgylegally run --count 10 --source youtube:7 --source local:3
```

## Output

```
dodgylegally_output/
├── raw/          Downloaded clips + JSON metadata sidecars
├── oneshot/      One-shot samples (2s, normalized, fade-out)
├── loop/         Loop samples (1s, cross-faded, seamless)
└── combined/     Combined loops (versioned: v1, v2, ...)
```

All output is standard WAV. Each clip has a `.json` sidecar tracking its source, query, URL, timestamps, and processing history.

## What you can do with it

- **Load one-shots into a sampler** and play them chromatically — a 1-second clip of someone talking becomes a melodic instrument.
- **Layer loops on a timeline** for evolving textures and ambient beds.
- **Feed combined files into a granular synthesizer** for further sound design.
- **Use clips as impulse responses** for convolution reverb — a 1-second recording of an unknown room gives you that room's acoustics.
- **Build themed sample packs** with custom word lists — weather sounds, industrial noise, spoken word fragments.
- **Compose structured pieces** by sorting clips by loudness and arranging them into arcs (see [case studies](docs/)).

## Case studies

Three documented experiments exploring different approaches:

- **[Making a Beat from Nothing](docs/case-study-making-a-beat-from-nothing.md)** — Random phrases, 14% hit rate, a 14-second piece from 4 surviving clips. The chaos approach.
- **[The Sound of Confetti](docs/case-study-confetti-tornado.md)** — Themed collection around "tornado full of confetti." 32 clips composed into a 36-second structured piece with an intro/build/peak/outro arc. Documents YouTube rate limiting and mitigation strategies.
- **[Super-Tight Word Isolation](docs/case-study-super-tight.md)** — Isolating spoken words from neighbouring speech bleed using whisper-detected word boundaries. 114 super-tight clips, a compatibility scorer, 20 assembled versions of "tornado full of confetti," and a composition suite exploring spectral morphing, reverse reveals, and rhythmic word scattering.

## Architecture

```
src/dodgylegally/
├── cli.py              Click CLI with subcommands
├── clip.py             Clip extraction config (position, duration)
├── search.py           Word list loading, phrase generation
├── download.py         Direct URL download (yt-dlp)
├── process.py          One-shot and loop processing (pydub)
├── combine.py          Versioned loop merging
├── config.py           YAML preset loading and merging
├── metadata.py         JSON sidecar system for provenance
├── analyze.py          BPM, key, loudness, spectral analysis
├── looping.py          BPM-aware loop creation, beat alignment
├── transform.py        Pitch shifting, time stretching
├── stems.py            Multi-track stem export
├── transcript.py       YouTube caption fetching, whisper transcription
├── ui.py               Console output (quiet/verbose modes)
├── logging_config.py   Structured logging configuration
├── wordlist.txt        Bundled 5,000-word dictionary
├── presets/            Bundled YAML presets
├── effects/            Pluggable audio effects (reverb, bitcrush, etc.)
├── strategies/         Arrangement strategies (tempo, key, layered, etc.)
├── templates/          YAML arrangement templates
└── sources/            Pluggable audio source system
    ├── base.py         AudioSource protocol, SearchResult, DownloadedClip
    ├── youtube.py      YouTube source (yt-dlp with retry/backoff)
    └── local.py        Local file source (random position extraction)
```

Each module exposes plain Python functions. The CLI is a thin layer on top. All inter-step communication happens through the filesystem. Sources, effects, and strategies are all protocol-based — implement the interface to add a new one.

## Development

```bash
# Install in dev mode
pip install -e .

# Run tests
pytest tests/ -v
```

283 tests covering CLI subcommands, clip extraction, source abstraction, local file sampling, metadata sidecars, weighted selection, download resilience, presets, logging, UI modes, audio processing, effects, BPM-aware looping, pitch/time transforms, arrangement strategies, templates, stems, and analysis.

## Origins

Originally a [Google Colab notebook](https://colab.research.google.com/github/danielraffel/dodgylegally/blob/main/dodgylegally.ipynb) hacked together by Daniel Raffel, based on work by [Colugo Music](https://x.com/ColugoMusic/status/1726001266180956440?s=20). The notebook is preserved in the repo for reference.

<a href="https://colab.research.google.com/github/danielraffel/dodgylegally/blob/main/dodgylegally.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg"></a>

## License

Public domain, based on a script by [Colugo Music](https://x.com/ColugoMusic/status/1726001266180956440?s=20) that was [released to the public domain](https://x.com/ColugoMusic/status/1726239468175417743?s=20). Use, modify, and distribute as you like.
