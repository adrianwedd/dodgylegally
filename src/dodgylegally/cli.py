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
@click.pass_context
def cli(ctx, output, verbose, quiet):
    """Creative audio sampling tool."""
    from dodgylegally.ui import Console

    ctx.ensure_object(dict)
    ctx.obj["output"] = output
    ctx.obj["console"] = Console(quiet=quiet, verbose=verbose)


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
@click.pass_context
def download(ctx, phrase, phrases_file, url):
    """Download audio from YouTube."""
    import os
    from dodgylegally.download import download_audio, download_url

    _check_ffmpeg()
    console = ctx.obj["console"]
    output_dir = os.path.join(ctx.obj["output"], "raw")
    if url:
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
    for p in phrases:
        console.info(f"Downloading: {p}")
        try:
            files = download_audio(p, output_dir)
            for f in files:
                console.info(f"  saved: {f}")
        except Exception as e:
            console.error(f"  download failed: {e}")


@cli.command()
@click.option("--input", "-i", "input_path", default=None, help="Input file or directory. Defaults to <output>/raw/.")
@click.pass_context
def process(ctx, input_path):
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
            result = process_file(filepath, oneshot_dir, loop_dir)
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
@click.pass_context
def run(ctx, count, wordlist):
    """Full pipeline: search -> download -> process -> combine."""
    import os
    from dodgylegally.search import load_wordlist, generate_phrases
    from dodgylegally.download import download_audio
    from dodgylegally.process import process_file as process_single
    from dodgylegally.combine import combine_loops

    _check_ffmpeg()
    console = ctx.obj["console"]
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
    console.info(f"Generated {len(phrases)} search phrases")

    # Download + Process
    for phrase in phrases:
        console.info(f"Downloading: {phrase}")
        try:
            new_files = download_audio(phrase, raw_dir)
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


if __name__ == "__main__":
    cli()
