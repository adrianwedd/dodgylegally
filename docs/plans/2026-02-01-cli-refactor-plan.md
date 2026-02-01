# dodgylegally CLI Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract the dodgylegally Colab notebook into an installable Python CLI with modular subcommands (search, download, process, combine, run).

**Architecture:** Click-based CLI with four backend modules (search, download, process, combine). Each module exposes plain Python functions. The CLI is a thin arg-parsing layer. All inter-step communication happens via the filesystem through a shared output directory.

**Tech Stack:** Python 3.10+, Click, pydub, yt-dlp, pytest. Requires FFmpeg at runtime.

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/dodgylegally/__init__.py`
- Create: `src/dodgylegally/cli.py` (stub)

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "dodgylegally"
version = "0.1.0"
description = "Creative audio sampling tool — generates random samples from YouTube"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "pydub>=0.25",
    "yt-dlp>=2023.0",
]

[project.scripts]
dodgylegally = "dodgylegally.cli:cli"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Create src/dodgylegally/__init__.py**

```python
"""dodgylegally — creative audio sampling tool."""
```

**Step 3: Create CLI stub**

```python
# src/dodgylegally/cli.py
import click

@click.group()
@click.option("--output", "-o", default="./dodgylegally_output", help="Output directory.")
@click.pass_context
def cli(ctx, output):
    """Creative audio sampling tool."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = output

if __name__ == "__main__":
    cli()
```

**Step 4: Install in dev mode and verify**

Run: `pip install -e ".[dev]"` then `dodgylegally --help`
Expected: Help text with `--output` option, no subcommands yet.

**Step 5: Commit**

```bash
git add pyproject.toml src/
git commit -m "feat: project scaffolding with Click CLI stub"
```

---

### Task 2: search module

**Files:**
- Create: `src/dodgylegally/wordlist.txt`
- Create: `src/dodgylegally/search.py`
- Create: `tests/test_search.py`
- Modify: `src/dodgylegally/cli.py`

**Step 1: Generate the bundled word list**

Create `src/dodgylegally/wordlist.txt` with ~5,000 common English words (one per line). Use a standard source like `/usr/share/dict/words` filtered to common 3-8 letter lowercase words, or a curated open-source word list. A larger list (vs the notebook's 200) ensures sufficient phrase variety without the NLTK runtime dependency.

**Step 2: Write failing tests**

```python
# tests/test_search.py
from dodgylegally.search import load_wordlist, generate_phrases

def test_load_default_wordlist():
    words = load_wordlist()
    assert isinstance(words, list)
    assert len(words) > 0
    assert all(isinstance(w, str) for w in words)

def test_load_custom_wordlist(tmp_path):
    f = tmp_path / "words.txt"
    f.write_text("alpha\nbeta\ngamma\n")
    words = load_wordlist(str(f))
    assert words == ["alpha", "beta", "gamma"]

def test_generate_phrases():
    words = ["alpha", "beta", "gamma", "delta"]
    phrases = generate_phrases(words, 3)
    assert len(phrases) == 3
    for phrase in phrases:
        parts = phrase.split()
        assert len(parts) == 2
        assert all(p in words for p in parts)

def test_generate_phrases_empty_count():
    words = ["alpha", "beta"]
    phrases = generate_phrases(words, 0)
    assert phrases == []
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/test_search.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dodgylegally.search'`

**Step 4: Implement search.py**

```python
# src/dodgylegally/search.py
import random
from importlib.resources import files

def load_wordlist(path: str | None = None) -> list[str]:
    """Load word list from file path, or bundled default."""
    if path is None:
        resource = files("dodgylegally").joinpath("wordlist.txt")
        text = resource.read_text()
    else:
        with open(path) as f:
            text = f.read()
    return [line.strip() for line in text.splitlines() if line.strip()]

def generate_phrases(word_list: list[str], count: int) -> list[str]:
    """Return count random 2-word phrases."""
    phrases = []
    for _ in range(count):
        words = random.sample(word_list, 2)
        phrases.append(" ".join(words))
    return phrases
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_search.py -v`
Expected: All 4 tests PASS.

**Step 6: Add search subcommand to CLI**

```python
# Add to src/dodgylegally/cli.py
import sys
from dodgylegally.search import load_wordlist, generate_phrases

@cli.command()
@click.option("--count", "-c", default=10, help="Number of phrases to generate.")
@click.option("--wordlist", "-w", default=None, help="Path to custom word list file.")
@click.option("--phrase", "-p", default=None, help="Use this phrase directly instead of generating.")
@click.pass_context
def search(ctx, count, wordlist, phrase):
    """Generate random search phrases."""
    if phrase:
        click.echo(phrase)
        return
    words = load_wordlist(wordlist)
    phrases = generate_phrases(words, count)
    for p in phrases:
        click.echo(p)
```

**Step 7: Verify CLI works**

Run: `dodgylegally search --count 3`
Expected: 3 random two-word phrases printed to stdout.

Run: `dodgylegally search --phrase "rain thunder"`
Expected: `rain thunder`

**Step 8: Commit**

```bash
git add src/dodgylegally/search.py src/dodgylegally/wordlist.txt src/dodgylegally/cli.py tests/test_search.py
git commit -m "feat: add search module with word list and CLI subcommand"
```

---

### Task 3: download module

**Files:**
- Create: `src/dodgylegally/download.py`
- Create: `tests/test_download.py`
- Modify: `src/dodgylegally/cli.py`

**Step 1: Write failing tests**

```python
# tests/test_download.py
import os
from unittest.mock import patch, MagicMock
from dodgylegally.download import download_audio, download_url, make_download_options

def test_make_download_options():
    opts = make_download_options("rain thunder", "/tmp/out")
    assert opts["format"] == "bestaudio/best"
    assert opts["paths"]["home"] == "/tmp/out"
    assert "rain thunder" in opts["outtmpl"]["default"]

def test_make_download_options_sanitizes_phrase():
    opts = make_download_options("bad/phrase!@#", "/tmp/out")
    template = opts["outtmpl"]["default"]
    assert "/" not in template.split("/")[-1].replace("%(", "").replace(")s", "")
    assert "!" not in template
    assert "@" not in template

@patch("dodgylegally.download.YoutubeDL")
def test_download_audio_calls_ytdlp(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
    download_audio("test phrase", str(tmp_path))
    mock_ydl.download.assert_called_once()

@patch("dodgylegally.download.YoutubeDL")
def test_download_url_calls_ytdlp(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
    download_url("https://youtube.com/watch?v=abc", str(tmp_path))
    mock_ydl.download.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_download.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement download.py**

```python
# src/dodgylegally/download.py
import os
import sys
from yt_dlp import YoutubeDL

class _DownloadRangeFunc:
    """Extract 1-second segment from video midpoint."""
    def __call__(self, info_dict, ydl):
        duration = info_dict.get("duration")
        timestamp = (duration / 2) if duration else 0
        yield {"start_time": timestamp, "end_time": timestamp}

def make_download_options(phrase: str, output_dir: str) -> dict:
    """Build yt-dlp options dict."""
    safe_phrase = "".join(x for x in phrase if x.isalnum() or x in "._- ")
    return {
        "format": "bestaudio/best",
        "paths": {"home": output_dir},
        "outtmpl": {"default": f"{safe_phrase}-%(id)s.%(ext)s"},
        "download_ranges": _DownloadRangeFunc(),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
        "no_warnings": True,
    }

def download_audio(phrase: str, output_dir: str) -> None:
    """Download 1s audio clip from YouTube search for phrase."""
    os.makedirs(output_dir, exist_ok=True)
    url = f'ytsearch1:"{phrase}"'
    opts = make_download_options(phrase, output_dir)
    with YoutubeDL(opts) as ydl:
        ydl.download([url])

def download_url(url: str, output_dir: str) -> None:
    """Download 1s audio clip from a specific YouTube URL."""
    os.makedirs(output_dir, exist_ok=True)
    opts = make_download_options("url_download", output_dir)
    with YoutubeDL(opts) as ydl:
        ydl.download([url])
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_download.py -v`
Expected: All 4 tests PASS.

**Step 5: Add download subcommand to CLI**

```python
# Add to src/dodgylegally/cli.py
import os
import sys
from dodgylegally.download import download_audio, download_url

@cli.command()
@click.option("--phrase", "-p", multiple=True, help="Search phrase(s) to download.")
@click.option("--phrases-file", "-f", type=click.File("r"), default=None, help="File with phrases, one per line. Use - for stdin.")
@click.option("--url", "-u", default=None, help="Direct YouTube URL to download.")
@click.pass_context
def download(ctx, phrase, phrases_file, url):
    """Download audio from YouTube."""
    output_dir = os.path.join(ctx.obj["output"], "raw")
    if url:
        click.echo(f"Downloading from URL: {url}", err=True)
        download_url(url, output_dir)
    phrases = list(phrase)
    if phrases_file:
        phrases.extend(line.strip() for line in phrases_file if line.strip())
    if not phrases and not url:
        raise click.UsageError("Provide --phrase, --phrases-file, or --url.")
    for p in phrases:
        click.echo(f"Downloading: {p}", err=True)
        download_audio(p, output_dir)
```

**Step 6: Verify CLI works**

Run: `dodgylegally download --phrase "rain thunder"`
Expected: Downloads audio to `./dodgylegally_output/raw/`

**Step 7: Commit**

```bash
git add src/dodgylegally/download.py src/dodgylegally/cli.py tests/test_download.py
git commit -m "feat: add download module with yt-dlp integration and CLI subcommand"
```

---

### Task 4: process module

**Files:**
- Create: `src/dodgylegally/process.py`
- Create: `tests/test_process.py`
- Modify: `src/dodgylegally/cli.py`

**Step 0: Add FFmpeg check utility**

Add a helper to `src/dodgylegally/cli.py` that verifies FFmpeg is available before running audio processing commands:

```python
import shutil

def _check_ffmpeg():
    """Check that FFmpeg is installed and available on PATH."""
    if not shutil.which("ffmpeg"):
        raise click.ClickException(
            "FFmpeg not found. Please install it to use audio processing features.\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )
```

Call `_check_ffmpeg()` at the start of the `process`, `combine`, and `run` subcommands.

**Step 1: Write failing tests**

```python
# tests/test_process.py
import os
from pydub import AudioSegment
from pydub.generators import WhiteNoise
from dodgylegally.process import make_oneshot, make_loop, process_file

def _make_test_wav(path, duration_ms=1500):
    """Create a test WAV file with white noise."""
    sound = WhiteNoise().to_audio_segment(duration=duration_ms)
    sound.export(path, format="wav")
    return path

def test_make_oneshot_creates_file(tmp_path):
    src = _make_test_wav(str(tmp_path / "input.wav"))
    out = str(tmp_path / "oneshot.wav")
    result = make_oneshot(src, out)
    assert os.path.exists(result)
    sound = AudioSegment.from_file(result)
    assert len(sound) <= 2000

def test_make_oneshot_caps_at_2000ms(tmp_path):
    src = _make_test_wav(str(tmp_path / "input.wav"), duration_ms=5000)
    out = str(tmp_path / "oneshot.wav")
    make_oneshot(src, out)
    sound = AudioSegment.from_file(out)
    assert len(sound) <= 2000

def test_make_loop_creates_file(tmp_path):
    src = _make_test_wav(str(tmp_path / "input.wav"))
    out = str(tmp_path / "loop.wav")
    result = make_loop(src, out)
    assert os.path.exists(result)

def test_process_file_creates_both(tmp_path):
    src = _make_test_wav(str(tmp_path / "input.wav"))
    oneshot_dir = str(tmp_path / "oneshot")
    loop_dir = str(tmp_path / "loop")
    os.makedirs(oneshot_dir)
    os.makedirs(loop_dir)
    result = process_file(src, oneshot_dir, loop_dir)
    assert len(result) == 2
    assert os.path.exists(result[0])
    assert os.path.exists(result[1])

def test_process_file_skips_short_audio(tmp_path):
    src = _make_test_wav(str(tmp_path / "input.wav"), duration_ms=200)
    oneshot_dir = str(tmp_path / "oneshot")
    loop_dir = str(tmp_path / "loop")
    os.makedirs(oneshot_dir)
    os.makedirs(loop_dir)
    result = process_file(src, oneshot_dir, loop_dir)
    assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_process.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement process.py**

```python
# src/dodgylegally/process.py
import os
from pydub import AudioSegment, effects

def make_oneshot(input_path: str, output_path: str) -> str:
    """Create one-shot sample: cap at 2000ms, fade out, normalize."""
    sound = AudioSegment.from_file(input_path, "wav")
    final_length = min(2000, len(sound))
    quarter = int(final_length / 4)
    sound = sound[:final_length]
    sound = sound.fade_out(duration=quarter)
    sound = effects.normalize(sound)
    sound.export(output_path, format="wav")
    return output_path

def make_loop(input_path: str, output_path: str) -> str:
    """Create loop sample: split, cross-fade, overlay, normalize."""
    sound = AudioSegment.from_file(input_path, "wav")
    final_length = min(2000, len(sound))
    half = int(final_length / 2)
    fade_length = int(final_length / 4)
    beg = sound[:half]
    end = sound[half:]
    end = end[:fade_length]
    beg = beg.fade_in(duration=fade_length)
    end = end.fade_out(duration=fade_length)
    sound = beg.overlay(end)
    sound = effects.normalize(sound)
    sound.export(output_path, format="wav")
    return output_path

def process_file(input_path: str, oneshot_dir: str, loop_dir: str) -> tuple[str, str] | None:
    """Process a single WAV into one-shot + loop variants. Returns paths or None if too short."""
    sound = AudioSegment.from_file(input_path, "wav")
    if len(sound) <= 500:
        return None
    basename = os.path.basename(input_path)
    oneshot_path = os.path.join(oneshot_dir, f"oneshot_{basename}")
    loop_path = os.path.join(loop_dir, f"loop_{basename}")
    make_oneshot(input_path, oneshot_path)
    make_loop(input_path, loop_path)
    return (oneshot_path, loop_path)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_process.py -v`
Expected: All 5 tests PASS.

**Step 5: Add process subcommand to CLI**

```python
# Add to src/dodgylegally/cli.py
import glob
from dodgylegally.process import process_file

@cli.command()
@click.option("--input", "-i", "input_path", default=None, help="Input file or directory. Defaults to <output>/raw/.")
@click.pass_context
def process(ctx, input_path):
    """Process audio files into one-shots and loops."""
    _check_ffmpeg()
    base = ctx.obj["output"]
    if input_path is None:
        input_path = os.path.join(base, "raw")
    oneshot_dir = os.path.join(base, "oneshot")
    loop_dir = os.path.join(base, "loop")
    os.makedirs(oneshot_dir, exist_ok=True)
    os.makedirs(loop_dir, exist_ok=True)

    if os.path.isfile(input_path):
        files = [input_path]
    else:
        files = glob.glob(os.path.join(input_path, "*.wav"))

    for filepath in files:
        click.echo(f"Processing: {os.path.basename(filepath)}", err=True)
        result = process_file(filepath, oneshot_dir, loop_dir)
        if result:
            click.echo(f"  oneshot: {result[0]}", err=True)
            click.echo(f"  loop:    {result[1]}", err=True)
        else:
            click.echo(f"  skipped (too short)", err=True)
```

**Step 6: Verify CLI works**

Run: `dodgylegally process --input path/to/some.wav`
Expected: Creates oneshot and loop files in output directory.

**Step 7: Commit**

```bash
git add src/dodgylegally/process.py src/dodgylegally/cli.py tests/test_process.py
git commit -m "feat: add process module with one-shot and loop generation"
```

---

### Task 5: combine module

**Files:**
- Create: `src/dodgylegally/combine.py`
- Create: `tests/test_combine.py`
- Modify: `src/dodgylegally/cli.py`

**Step 1: Write failing tests**

```python
# tests/test_combine.py
import os
from pydub import AudioSegment
from pydub.generators import WhiteNoise
from dodgylegally.combine import combine_loops

def _make_test_wav(path, duration_ms=500):
    sound = WhiteNoise().to_audio_segment(duration=duration_ms)
    sound.export(path, format="wav")

def test_combine_loops_creates_file(tmp_path):
    loop_dir = tmp_path / "loop"
    loop_dir.mkdir()
    _make_test_wav(str(loop_dir / "loop1.wav"))
    _make_test_wav(str(loop_dir / "loop2.wav"))
    out_dir = str(tmp_path / "combined")
    result = combine_loops(str(loop_dir), out_dir)
    assert os.path.exists(result)
    assert "combined_loop_v1.wav" in result

def test_combine_loops_increments_version(tmp_path):
    loop_dir = tmp_path / "loop"
    loop_dir.mkdir()
    _make_test_wav(str(loop_dir / "loop1.wav"))
    out_dir = str(tmp_path / "combined")
    r1 = combine_loops(str(loop_dir), out_dir)
    r2 = combine_loops(str(loop_dir), out_dir)
    assert "v1" in r1
    assert "v2" in r2

def test_combine_loops_empty_dir(tmp_path):
    loop_dir = tmp_path / "loop"
    loop_dir.mkdir()
    out_dir = str(tmp_path / "combined")
    result = combine_loops(str(loop_dir), out_dir)
    assert result is None

def test_combine_loops_custom_repeats(tmp_path):
    loop_dir = tmp_path / "loop"
    loop_dir.mkdir()
    _make_test_wav(str(loop_dir / "loop1.wav"), duration_ms=200)
    out_dir = str(tmp_path / "combined")
    result = combine_loops(str(loop_dir), out_dir, repeats=(2, 2))
    assert os.path.exists(result)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_combine.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement combine.py**

```python
# src/dodgylegally/combine.py
import os
import glob
import random
from pydub import AudioSegment

def combine_loops(loop_dir: str, output_dir: str, repeats: tuple[int, int] = (3, 4)) -> str | None:
    """Combine all loops into a versioned file. Returns output path, or None if no loops."""
    wav_files = glob.glob(os.path.join(loop_dir, "*.wav"))
    if not wav_files:
        return None

    os.makedirs(output_dir, exist_ok=True)
    combined = AudioSegment.silent(duration=100)

    for filepath in wav_files:
        sound = AudioSegment.from_file(filepath, format="wav")
        repeat_count = random.randint(repeats[0], repeats[1])
        combined += sound * repeat_count

    version = 1
    while True:
        output_path = os.path.join(output_dir, f"combined_loop_v{version}.wav")
        if not os.path.exists(output_path):
            break
        version += 1

    combined.export(output_path, format="wav")
    return output_path
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_combine.py -v`
Expected: All 4 tests PASS.

**Step 5: Add combine subcommand to CLI**

```python
# Add to src/dodgylegally/cli.py
from dodgylegally.combine import combine_loops

@cli.command()
@click.option("--input", "-i", "input_dir", default=None, help="Directory with loop files. Defaults to <output>/loop/.")
@click.option("--repeats", "-r", default="3-4", help="Repeat range for each loop (e.g. 3-4).")
@click.pass_context
def combine(ctx, input_dir, repeats):
    """Merge loop files into a combined file."""
    _check_ffmpeg()
    base = ctx.obj["output"]
    if input_dir is None:
        input_dir = os.path.join(base, "loop")
    output_dir = os.path.join(base, "combined")

    parts = repeats.split("-")
    repeat_range = (int(parts[0]), int(parts[1]))

    result = combine_loops(input_dir, output_dir, repeats=repeat_range)
    if result:
        click.echo(f"Combined loop: {result}", err=True)
    else:
        click.echo("No loop files found to combine.", err=True)
```

**Step 6: Commit**

```bash
git add src/dodgylegally/combine.py src/dodgylegally/cli.py tests/test_combine.py
git commit -m "feat: add combine module with versioned loop merging"
```

---

### Task 6: run subcommand (full pipeline)

**Files:**
- Modify: `src/dodgylegally/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write failing test**

```python
# tests/test_cli.py
from click.testing import CliRunner
from dodgylegally.cli import cli

def test_search_subcommand():
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--count", "3"])
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert len(lines) == 3

def test_search_with_phrase():
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--phrase", "rain thunder"])
    assert result.exit_code == 0
    assert "rain thunder" in result.output

def test_run_requires_count():
    runner = CliRunner()
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0 or "count" in result.output.lower() or "count" in (result.stderr or "").lower()
```

**Step 2: Run tests to verify they fail (partially)**

Run: `pytest tests/test_cli.py -v`
Expected: First two PASS (search already works), third FAIL (run subcommand doesn't exist).

**Step 3: Implement run subcommand**

```python
# Add to src/dodgylegally/cli.py
from dodgylegally.search import load_wordlist, generate_phrases
from dodgylegally.download import download_audio
from dodgylegally.process import process_file as process_single
from dodgylegally.combine import combine_loops

@cli.command()
@click.option("--count", "-c", required=True, type=int, help="Number of samples to generate.")
@click.option("--wordlist", "-w", default=None, help="Path to custom word list file.")
@click.pass_context
def run(ctx, count, wordlist):
    """Full pipeline: search -> download -> process -> combine."""
    base = ctx.obj["output"]
    raw_dir = os.path.join(base, "raw")
    oneshot_dir = os.path.join(base, "oneshot")
    loop_dir = os.path.join(base, "loop")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(oneshot_dir, exist_ok=True)
    os.makedirs(loop_dir, exist_ok=True)

    # Search
    words = load_wordlist(wordlist)
    phrases = generate_phrases(words, count)
    click.echo(f"Generated {len(phrases)} search phrases", err=True)

    _check_ffmpeg()

    # Download + Process
    for phrase in phrases:
        click.echo(f"Downloading: {phrase}", err=True)
        try:
            download_audio(phrase, raw_dir)
        except Exception as e:
            click.echo(f"  download failed: {e}", err=True)
            continue
        for filepath in glob.glob(os.path.join(raw_dir, "*.wav")):
            click.echo(f"Processing: {os.path.basename(filepath)}", err=True)
            try:
                result = process_single(filepath, oneshot_dir, loop_dir)
                if result:
                    click.echo(f"  oneshot: {result[0]}", err=True)
                    click.echo(f"  loop:    {result[1]}", err=True)
            except Exception as e:
                click.echo(f"  processing failed: {e}", err=True)
            try:
                os.remove(filepath)
            except OSError:
                pass

    # Combine
    combined = combine_loops(loop_dir, os.path.join(base, "combined"))
    if combined:
        click.echo(f"Combined loop: {combined}", err=True)
    click.echo("Done.", err=True)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add src/dodgylegally/cli.py tests/test_cli.py
git commit -m "feat: add run subcommand for full pipeline execution"
```

---

### Task 7: Update CLAUDE.md and README

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Step 1: Update CLAUDE.md**

Update to reflect the new project structure: CLI commands, module layout, how to install and develop, how to run tests.

**Step 2: Update README.md**

Update to document the CLI interface, installation instructions (`pip install .`), usage examples for each subcommand, and the piping workflow.

**Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update CLAUDE.md and README for CLI tool"
```

---

### Task 8: Integration smoke test

**Step 1: Full pipeline test**

Run manually to verify end-to-end:
```bash
dodgylegally run --count 2 -o /tmp/dodgylegally_test
ls /tmp/dodgylegally_test/oneshot/
ls /tmp/dodgylegally_test/loop/
ls /tmp/dodgylegally_test/combined/
```
Expected: WAV files in each directory.

**Step 2: Piping test**

```bash
dodgylegally search --count 2 | dodgylegally download --phrases-file -
dodgylegally process
dodgylegally combine
```
Expected: Same result via composed subcommands.

**Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: integration test fixes"
```
