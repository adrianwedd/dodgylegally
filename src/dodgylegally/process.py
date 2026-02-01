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
    """Create loop sample: split, cross-fade, overlay, normalize.

    Note: end = end[:fade_length] discards most of the second half.
    This matches the original notebook behavior.
    """
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


def process_file(input_path: str, oneshot_dir: str, loop_dir: str, effect_chain=None) -> tuple[str, str] | None:
    """Process a single WAV into one-shot + loop variants. Returns paths or None if too short.

    If effect_chain is provided, applies it to the audio before processing.
    """
    sound = AudioSegment.from_file(input_path, "wav")
    if len(sound) <= 500:
        return None

    basename = os.path.basename(input_path)
    actual_input = input_path

    if effect_chain is not None:
        import tempfile
        sound = effect_chain.apply(sound)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sound.export(tmp.name, format="wav")
        actual_input = tmp.name

    oneshot_path = os.path.join(oneshot_dir, f"oneshot_{basename}")
    loop_path = os.path.join(loop_dir, f"loop_{basename}")
    make_oneshot(actual_input, oneshot_path)
    make_loop(actual_input, loop_path)

    if effect_chain is not None:
        try:
            os.remove(actual_input)
        except OSError:
            pass

    return (oneshot_path, loop_path)
