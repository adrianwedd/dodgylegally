# dodgylegally

You type a number. The machine picks two words at random — *spinelet digeny*, *goshen duress*, *befit zygote* — searches YouTube for each absurd phrase, grabs one second of audio from the middle of whatever it finds, and hands you back a sample you never could have imagined.

Do it ten times and you have a sample pack. Do it a hundred times and you have an instrument.

**dodgylegally** is a CLI tool for generating audio samples from the chaos of YouTube. It searches, downloads, processes, and combines — turning random words into one-shots, loops, and compositions.

---

## How it works

```
words ──→ phrases ──→ YouTube ──→ audio ──→ samples
```

1. **Search** — Pairs random words from a 5,000-word dictionary into phrases no human would type.
2. **Download** — Searches YouTube for each phrase. Extracts a 1-second clip from the midpoint of the first result.
3. **Process** — Shapes each clip into two variants: a **one-shot** (2s max, normalized, fade-out) and a **loop** (1s, cross-faded for seamless repeat).
4. **Combine** — Stitches all loops together, each repeated 3-4 times, into a single versioned file.

Every run produces different output. Two people running the same command will get completely different audio.

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
# 10 random samples
dodgylegally run --count 10

# Custom output directory
dodgylegally run --count 5 -o ~/Music/samples

# Use a themed word list
dodgylegally run --count 20 --wordlist weather_words.txt
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

# Download from a direct URL
dodgylegally download --url "https://youtube.com/watch?v=..."

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

### Custom word lists

The built-in dictionary has 5,000 words. For themed collections, supply your own:

```bash
echo -e "rain\nthunder\nstorm\nlightning\ndrizzle\nhail" > weather.txt
dodgylegally run --count 10 --wordlist weather.txt
```

The phrases will still be random pairs (*thunder drizzle*, *hail storm*), but the source material will skew toward weather-related videos.

## Output

```
dodgylegally_output/
├── raw/          Downloaded clips (1-10s each)
├── oneshot/      One-shot samples (2s, normalized, fade-out)
├── loop/         Loop samples (1s, cross-faded, seamless)
└── combined/     Combined loops (versioned: v1, v2, ...)
```

All output is standard WAV. Load into any DAW, sampler, or audio tool.

## What you can do with it

- **Load one-shots into a sampler** and play them chromatically — a 1-second clip of someone talking becomes a melodic instrument.
- **Layer loops on a timeline** for evolving textures and ambient beds.
- **Feed combined files into a granular synthesizer** for further sound design.
- **Use clips as impulse responses** for convolution reverb — a 1-second recording of an unknown room gives you that room's acoustics.
- **Build themed sample packs** with custom word lists — weather sounds, industrial noise, spoken word fragments.
- **Compose structured pieces** by sorting clips by loudness and arranging them into arcs (see [case studies](docs/)).

## Case studies

Two documented experiments exploring different approaches:

- **[Making a Beat from Nothing](docs/case-study-making-a-beat-from-nothing.md)** — Random phrases, 14% hit rate, a 14-second piece from 4 surviving clips. The chaos approach.
- **[The Sound of Confetti](docs/case-study-confetti-tornado.md)** — Themed collection around "tornado full of confetti." 32 clips composed into a 36-second structured piece with an intro/build/peak/outro arc. Documents YouTube rate limiting and mitigation strategies.

## Architecture

```
src/dodgylegally/
├── cli.py          Click CLI with subcommands
├── search.py       Word list loading, phrase generation
├── download.py     yt-dlp wrapper, midpoint extraction
├── process.py      One-shot and loop processing (pydub)
├── combine.py      Versioned loop merging
└── wordlist.txt    Bundled 5,000-word dictionary
```

Each module exposes plain Python functions. The CLI is a thin layer on top. All inter-step communication happens through the filesystem.

## Development

```bash
# Install in dev mode
pip install -e .

# Run tests
pytest tests/ -v
```

30 tests covering CLI subcommands, download options, audio processing, loop combining, phrase generation, and input validation.

## Origins

Originally a [Google Colab notebook](https://colab.research.google.com/github/danielraffel/dodgylegally/blob/main/dodgylegally.ipynb) hacked together by Daniel Raffel, based on work by [Colugo Music](https://x.com/ColugoMusic/status/1726001266180956440?s=20). The notebook is preserved in the repo for reference.

<a href="https://colab.research.google.com/github/danielraffel/dodgylegally/blob/main/dodgylegally.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg"></a>

## License

Public domain, based on a script by [Colugo Music](https://x.com/ColugoMusic/status/1726001266180956440?s=20) that was [released to the public domain](https://x.com/ColugoMusic/status/1726239468175417743?s=20). Use, modify, and distribute as you like.
