import shutil

import click


def _check_ffmpeg():
    """Check that FFmpeg is installed and available on PATH."""
    if not shutil.which("ffmpeg"):
        raise click.ClickException(
            "FFmpeg not found. Please install it to use audio processing features.\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )


def _parse_repeats(value: str) -> tuple[int, int]:
    """Parse a 'MIN-MAX' repeats string into a tuple. Raises click.BadParameter on invalid input."""
    try:
        parts = value.split("-")
        if len(parts) != 2:
            raise ValueError
        result = (int(parts[0]), int(parts[1]))
        if result[0] < 1 or result[1] < result[0]:
            raise ValueError
        return result
    except (ValueError, IndexError):
        raise click.BadParameter(f"Expected format: MIN-MAX (e.g. 3-4), got '{value}'.")


class _MutuallyExclusiveOption(click.Option):
    """Click option that is mutually exclusive with another option."""

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop("mutually_exclusive", []))
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        for name in self.mutually_exclusive:
            if name in opts and self.name in opts:
                raise click.UsageError(
                    f"--{self.name} and --{name} are mutually exclusive."
                )
        return super().handle_parse_result(ctx, opts, args)


@click.group()
@click.option("--output", "-o", default="./dodgylegally_output", help="Output directory.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show debug output.", cls=_MutuallyExclusiveOption, mutually_exclusive=["quiet"])
@click.option("--quiet", "-q", is_flag=True, default=False, help="Suppress all output except errors.", cls=_MutuallyExclusiveOption, mutually_exclusive=["verbose"])
@click.option("--log-file", default=None, type=click.Path(), help="Write structured log to file.")
@click.pass_context
def cli(ctx, output, verbose, quiet, log_file):
    """Creative audio sampling tool."""
    from dodgylegally.ui import Console
    from dodgylegally.logging_config import setup_logging

    ctx.ensure_object(dict)
    ctx.obj["output"] = output
    ctx.obj["console"] = Console(quiet=quiet, verbose=verbose)
    ctx.obj["logger"] = setup_logging(verbose=verbose, quiet=quiet, log_file=log_file)


@cli.command()
@click.option("--count", "-c", default=10, help="Number of phrases to generate.")
@click.option("--wordlist", "-w", default=None, help="Path to custom word list file.")
@click.option("--phrase", "-p", default=None, help="Use this phrase directly instead of generating.")
@click.pass_context
def search(ctx, count, wordlist, phrase):
    """Generate random search phrases."""
    from dodgylegally.search import load_wordlist, generate_phrases

    if phrase:
        click.echo(phrase)
        return
    words = load_wordlist(wordlist)
    phrases = generate_phrases(words, count)
    for p in phrases:
        click.echo(p)


@cli.command()
@click.option("--phrase", "-p", multiple=True, help="Search phrase(s) to download.")
@click.option("--phrases-file", "-f", type=click.File("r"), default=None, help="File with phrases, one per line. Use - for stdin.")
@click.option("--url", "-u", default=None, help="Direct YouTube URL to download.")
@click.option("--delay", "-d", default=0.0, type=float, help="Seconds to wait between downloads.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be downloaded without doing it.")
@click.option("--source", "-s", default="youtube", help="Audio source to use (e.g. youtube, freesound, local).")
@click.pass_context
def download(ctx, phrase, phrases_file, url, delay, dry_run, source):
    """Download audio from YouTube or other sources."""
    import os
    import time as _time
    from pathlib import Path
    from dodgylegally.sources import get_source

    if not dry_run:
        _check_ffmpeg()
    console = ctx.obj["console"]
    output_dir = os.path.join(ctx.obj["output"], "raw")
    audio_source = get_source(source)

    if url and not dry_run:
        from dodgylegally.download import download_url
        console.info(f"Downloading from URL: {url}")
        try:
            files = download_url(url, output_dir)
            for f in files:
                console.info(f"  saved: {f}")
        except Exception as e:
            console.error(f"  download failed: {e}")
    phrases = list(phrase)
    if phrases_file:
        phrases.extend(line.strip() for line in phrases_file if line.strip())
    if not phrases and not url:
        raise click.UsageError("Provide --phrase, --phrases-file, or --url.")
    for i, p in enumerate(phrases):
        if dry_run:
            info = audio_source.dry_run(p)
            console.info(f"[dry-run] {info['phrase']} -> {info['url']}")
        else:
            if i > 0 and delay > 0:
                _time.sleep(delay)
            console.info(f"Downloading ({audio_source.name}): {p}")
            try:
                results = audio_source.search(p)
                if not results:
                    console.info(f"  no results for '{p}'")
                    continue
                clip = audio_source.download(results[0], Path(output_dir), delay=delay)
                console.info(f"  saved: {clip.path}")
            except Exception as e:
                console.error(f"  download failed: {e}")


@cli.command()
@click.option("--input", "-i", "input_path", default=None, help="Input file or directory. Defaults to <output>/raw/.")
@click.option("--effects", "-e", default=None, help="Effect chain (e.g. 'reverb:0.5,lowpass:3000,bitcrush:8').")
@click.option("--target-bpm", default=None, type=float, help="Target BPM for beat-aligned loops.")
@click.option("--stretch", default=None, type=float, help="Time-stretch rate (e.g. 1.5 = 150%% speed).")
@click.option("--pitch", default=None, type=float, help="Pitch-shift in semitones (e.g. +3 or -2).")
@click.option("--target-key", default=None, help="Shift all samples to this key (e.g. 'C minor').")
@click.pass_context
def process(ctx, input_path, effects, target_bpm, stretch, pitch, target_key):
    """Process audio files into one-shots and loops."""
    import glob
    import os
    from dodgylegally.process import process_file

    _check_ffmpeg()
    base = ctx.obj["output"]
    if input_path is None:
        input_path = os.path.join(base, "raw")
    oneshot_dir = os.path.join(base, "oneshot")
    loop_dir = os.path.join(base, "loop")
    os.makedirs(oneshot_dir, exist_ok=True)
    os.makedirs(loop_dir, exist_ok=True)

    effect_chain = None
    if effects:
        from dodgylegally.effects import parse_chain
        effect_chain = parse_chain(effects)

    console = ctx.obj["console"]
    if os.path.isfile(input_path):
        files = [input_path]
    elif os.path.isdir(input_path):
        files = glob.glob(os.path.join(input_path, "*.wav"))
        if not files:
            console.info(f"No WAV files found in {input_path}")
            return
    else:
        raise click.BadParameter(f"Input path does not exist: {input_path}")

    for filepath in files:
        console.info(f"Processing: {os.path.basename(filepath)}")
        try:
            result = process_file(filepath, oneshot_dir, loop_dir, effect_chain=effect_chain)
            if result:
                console.info(f"  oneshot: {result[0]}")
                console.info(f"  loop:    {result[1]}")
            else:
                console.info("  skipped (too short)")
        except Exception as e:
            console.error(f"  processing failed: {e}")


@cli.command()
@click.option("--input", "-i", "input_dir", default=None, help="Directory with loop files. Defaults to <output>/loop/.")
@click.option("--repeats", "-r", default="3-4", help="Repeat range for each loop (e.g. 3-4).")
@click.pass_context
def combine(ctx, input_dir, repeats):
    """Merge loop files into a combined file."""
    import os
    from dodgylegally.combine import combine_loops

    _check_ffmpeg()
    repeat_range = _parse_repeats(repeats)
    base = ctx.obj["output"]
    if input_dir is None:
        input_dir = os.path.join(base, "loop")
    output_dir = os.path.join(base, "combined")

    console = ctx.obj["console"]
    result = combine_loops(input_dir, output_dir, repeats=repeat_range)
    if result:
        console.info(f"Combined loop: {result}")
    else:
        console.info("No loop files found to combine.")


@cli.command()
@click.option("--count", "-c", required=True, type=int, help="Number of samples to generate.")
@click.option("--wordlist", "-w", default=None, help="Path to custom word list file.")
@click.option("--delay", "-d", default=None, type=float, help="Seconds to wait between downloads.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be done without doing it.")
@click.option("--preset", default=None, help="Load config from a named preset (e.g. ambient, percussive).")
@click.option("--source", "-s", multiple=True, default=None, help="Audio source with optional weight (e.g. youtube:7, local:3). Repeatable.")
@click.pass_context
def run(ctx, count, wordlist, delay, dry_run, preset, source):
    """Full pipeline: search -> download -> process -> combine."""
    import os
    import time as _time
    from pathlib import Path
    from dodgylegally.search import load_wordlist, generate_phrases
    from dodgylegally.sources import get_source, parse_source_weight, weighted_select
    from dodgylegally.process import process_file as process_single
    from dodgylegally.combine import combine_loops

    # Apply preset config, CLI flags override
    if preset:
        from dodgylegally.config import load_preset, merge_config
        preset_cfg = load_preset(preset)
        overrides = {"count": count, "delay": delay}
        cfg = merge_config(preset_cfg, overrides)
        count = cfg.get("count", count)
        delay = cfg.get("delay", delay)

    if delay is None:
        delay = 0.0

    # Parse source weights
    if source:
        source_weights = [parse_source_weight(s) for s in source]
    else:
        source_weights = [("youtube", 1)]

    if not dry_run:
        _check_ffmpeg()
    console = ctx.obj["console"]
    base = ctx.obj["output"]
    raw_dir = os.path.join(base, "raw")
    oneshot_dir = os.path.join(base, "oneshot")
    loop_dir = os.path.join(base, "loop")

    # Search
    words = load_wordlist(wordlist)
    phrases = generate_phrases(words, count)
    console.info(f"Generated {len(phrases)} search phrases")

    if dry_run:
        for phrase in phrases:
            source_name = weighted_select(source_weights)
            src = get_source(source_name)
            info = src.dry_run(phrase)
            console.info(f"[dry-run] ({source_name}) {info['phrase']} -> {info.get('url', 'N/A')}")
        console.info(f"[dry-run] Would download {len(phrases)} clips, process, and combine.")
        return

    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(oneshot_dir, exist_ok=True)
    os.makedirs(loop_dir, exist_ok=True)

    # Download + Process
    for i, phrase in enumerate(phrases):
        if i > 0 and delay > 0:
            _time.sleep(delay)
        source_name = weighted_select(source_weights)
        audio_source = get_source(source_name)
        console.info(f"Downloading ({source_name}): {phrase}")
        try:
            results = audio_source.search(phrase)
            if not results:
                console.info(f"  no results for '{phrase}'")
                continue
            clip = audio_source.download(results[0], Path(raw_dir), delay=delay)
            new_files = [str(clip.path)]
        except Exception as e:
            console.error(f"  download failed: {e}")
            continue
        for filepath in new_files:
            console.info(f"Processing: {os.path.basename(filepath)}")
            try:
                result = process_single(filepath, oneshot_dir, loop_dir)
                if result:
                    console.info(f"  oneshot: {result[0]}")
                    console.info(f"  loop:    {result[1]}")
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            except Exception as e:
                console.error(f"  processing failed: {e}")

    # Combine
    combined = combine_loops(loop_dir, os.path.join(base, "combined"))
    if combined:
        console.info(f"Combined loop: {combined}")
    console.info("Done.")


@cli.command()
@click.option("--input", "-i", "input_path", default=None, help="File or directory to analyze. Defaults to <output>/raw/.")
@click.option("--no-cache", is_flag=True, default=False, help="Force re-analysis, ignore cached results.")
@click.pass_context
def analyze(ctx, input_path, no_cache):
    """Analyze audio files for BPM, key, loudness, and spectral features."""
    import glob
    import os
    from dodgylegally.analyze import analyze_file

    base = ctx.obj["output"]
    if input_path is None:
        input_path = os.path.join(base, "raw")
    console = ctx.obj["console"]

    if os.path.isfile(input_path):
        files = [input_path]
    elif os.path.isdir(input_path):
        files = glob.glob(os.path.join(input_path, "*.wav"))
        if not files:
            console.info(f"No WAV files found in {input_path}")
            return
    else:
        raise click.BadParameter(f"Input path does not exist: {input_path}")

    use_cache = not no_cache
    for filepath in sorted(files):
        name = os.path.basename(filepath)
        try:
            result = analyze_file(filepath, use_cache=use_cache)
            console.info(f"{name}: bpm={result.bpm} key={result.key} lufs={result.loudness_lufs} rms={result.rms_energy}")
        except Exception as e:
            console.error(f"{name}: analysis failed: {e}")


if __name__ == "__main__":
    cli()
