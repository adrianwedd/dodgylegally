# dodgylegally CLI Refactor — Solution Design

## Problem

dodgylegally exists as a single Google Colab notebook. It can't be used outside Colab, can't be called programmatically, and its pipeline steps (search, download, process, combine) are coupled together. We want to extract it into a proper Python CLI tool with modular subcommands.

## Goals

- Extract notebook code into an installable Python package with a `dodgylegally` CLI command
- Break the monolithic pipeline into independent subcommands: `search`, `download`, `process`, `combine`, `run`
- Remove Google Colab/Drive dependencies — work on any local filesystem
- Remove NLTK runtime dependency — ship a bundled word list
- Each subcommand operates independently on the filesystem via a shared output directory

## Non-Goals

- HTTP API or MCP server (future work)
- GUI or web interface
- Audio format conversion beyond WAV
- Streaming or real-time processing

## Architecture

```
CLI (cli.py / Click)
  |
  |-- search  -->  search.py   --> phrases to stdout or file
  |-- download --> download.py  --> WAV files in <output>/raw/
  |-- process  --> process.py   --> WAV files in <output>/oneshot/ and <output>/loop/
  |-- combine  --> combine.py   --> versioned WAV in <output>/combined/
  |-- run      --> orchestrates all of the above in sequence
```

Each module exposes plain Python functions. The CLI is a thin layer that parses arguments and calls them. All inter-step communication happens via the filesystem (the shared `--output` directory).

## Project Structure

```
dodgylegally/
├── pyproject.toml
├── src/
│   └── dodgylegally/
│       ├── __init__.py
│       ├── cli.py
│       ├── search.py
│       ├── download.py
│       ├── process.py
│       ├── combine.py
│       └── wordlist.txt
├── tests/
│   ├── test_search.py
│   ├── test_download.py
│   ├── test_process.py
│   └── test_combine.py
├── docs/
│   └── plans/
├── CLAUDE.md
└── README.md
```

## CLI Interface

```
dodgylegally [--output DIR] <command> [options]

Global options:
  --output, -o DIR    Output directory (default: ./dodgylegally_output)

Commands:
  search     Generate random search phrases
  download   Download audio from YouTube
  process    Process audio files into one-shots and loops
  combine    Merge loop files into a combined file
  run        Full pipeline (search -> download -> process -> combine)
```

### Subcommands

**search**
```
dodgylegally search --count N [--wordlist FILE] [--phrase "specific words"]
```
- Generates N random 2-word phrases from the word list
- `--wordlist` overrides the bundled default
- `--phrase` bypasses random generation, outputs the given phrase directly
- Output: one phrase per line to stdout

**download**
```
dodgylegally download [--phrase "words"] [--phrases-file FILE] [--url URL]
```
- At least one source required: `--phrase`, `--phrases-file` (use `-` for stdin), or `--url`
- Downloads 1-second audio clip from YouTube video midpoint
- Output: WAV files in `<output>/raw/`

**process**
```
dodgylegally process [--input DIR|FILE]
```
- Defaults to `<output>/raw/`
- Creates one-shot (capped 2000ms, quarter-length fade-out, normalized) and loop (split, cross-fade, overlay, normalized) variants
- Output: `<output>/oneshot/` and `<output>/loop/`

**combine**
```
dodgylegally combine [--input DIR] [--repeats MIN-MAX]
```
- Defaults to `<output>/loop/`
- Concatenates all loops, each repeated randomly within the repeats range (default 3-4)
- Auto-increments version number to avoid overwrites
- Output: `<output>/combined/combined_loop_vN.wav`

**run**
```
dodgylegally run --count N [--wordlist FILE]
```
- Executes full pipeline: search -> download -> process -> combine
- Equivalent to piping the subcommands together

### Piping Support

`search` outputs to stdout so subcommands compose:
```bash
dodgylegally search --count 5 | dodgylegally download --phrases-file -
```

Progress messages go to stderr to keep stdout clean.

## Module Design

### search.py

```python
def load_wordlist(path: str | None = None) -> list[str]:
    """Load word list from file, or bundled default."""

def generate_phrases(word_list: list[str], count: int) -> list[str]:
    """Return count random 2-word phrases."""
```

The bundled `wordlist.txt` contains ~5,000 common English words (not 200 as in the original notebook) to provide sufficient phrase variety without the NLTK dependency.

No side effects. Pure functions.

### download.py

```python
def download_audio(query: str, output_dir: str) -> str | None:
    """Download 1s audio clip from YouTube search. Returns output path."""

def download_url(url: str, output_dir: str) -> str | None:
    """Download 1s audio clip from specific URL. Returns output path."""
```

Wraps yt-dlp. The `download_range_func` class lives here.

### process.py

```python
def make_oneshot(input_path: str, output_path: str) -> str:
    """Create one-shot sample. Returns output path."""

def make_loop(input_path: str, output_path: str) -> str:
    """Create loop sample. Returns output path."""

def process_file(input_path: str, oneshot_dir: str, loop_dir: str) -> tuple[str, str]:
    """Process a single WAV into one-shot + loop. Returns both paths."""
```

Audio processing logic unchanged from notebook.

### combine.py

```python
def combine_loops(loop_dir: str, output_dir: str, repeats: tuple[int, int] = (3, 4)) -> str:
    """Combine all loops into versioned file. Returns output path."""
```

### cli.py

Click group with subcommands. Each subcommand is ~10-20 lines: parse args, call module function, print output.

## Dependencies

- `click` — CLI framework
- `pydub` — audio processing
- `yt-dlp` — YouTube downloading

Runtime requirement: FFmpeg (for pydub WAV conversion). The CLI checks for FFmpeg availability at startup of `process` and `run` commands, printing a helpful error if missing.

Removed: `nltk`, `glob2`, `google-colab`.

## Error Handling

- Module functions raise exceptions on failure
- CLI catches exceptions and prints clean error messages to stderr
- Non-zero exit codes on failure
- Individual file failures in batch operations (both download and processing steps) are logged but don't abort the batch
- FFmpeg availability is checked before audio processing commands

## Output Directory Layout

```
<output>/
├── raw/          # Downloaded audio clips
├── oneshot/      # One-shot processed samples
├── loop/         # Loop processed samples
└── combined/     # Combined loop files (versioned)
```
