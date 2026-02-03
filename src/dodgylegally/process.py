import os

import numpy as np
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
        tmp.close()
        sound.export(tmp.name, format="wav")
        actual_input = tmp.name

    oneshot_path = os.path.join(oneshot_dir, f"oneshot_{basename}")
    loop_path = os.path.join(loop_dir, f"loop_{basename}")
    try:
        make_oneshot(actual_input, oneshot_path)
        make_loop(actual_input, loop_path)
    finally:
        if effect_chain is not None:
            try:
                os.remove(actual_input)
            except OSError:
                pass

    return (oneshot_path, loop_path)


def trim_word_centered(
    audio: AudioSegment,
    word_start_s: float,
    word_end_s: float,
    clip_duration_s: float = 1.0,
    fade_ms: int = 8,
    zero_cross: bool = True,
    pad_ms: int = 50,
) -> AudioSegment:
    """Trim audio so the word sits at the center of the clip.

    Computes the word midpoint, centers a clip window around it,
    clamps to audio boundaries, optionally snaps edges to zero crossings,
    and applies micro-fades.

    When clip_duration_s=0 (word-boundary mode), trims to just the whisper
    word boundaries plus pad_ms on each side, instead of a fixed-length window.
    """
    from dodgylegally.looping import find_zero_crossing

    audio_duration_s = len(audio) / 1000.0

    if clip_duration_s == 0:
        # Word-boundary mode: use whisper boundaries + pad
        pad_s = pad_ms / 1000.0
        start_s = word_start_s - pad_s
        end_s = word_end_s + pad_s
    else:
        word_mid = (word_start_s + word_end_s) / 2.0
        half_clip = clip_duration_s / 2.0

        # Center window around word midpoint
        start_s = word_mid - half_clip
        end_s = word_mid + half_clip

    # Clamp to audio boundaries
    if clip_duration_s != 0:
        # Fixed-duration mode: shift window to preserve clip length
        if start_s < 0:
            end_s -= start_s  # shift right
            start_s = 0
        if end_s > audio_duration_s:
            start_s -= end_s - audio_duration_s  # shift left
            end_s = audio_duration_s
    start_s = max(0, start_s)
    end_s = min(end_s, audio_duration_s)

    start_ms = int(start_s * 1000)
    end_ms = int(end_s * 1000)
    trimmed = audio[start_ms:end_ms]

    if zero_cross and len(trimmed) > 0:
        samples = np.array(trimmed.get_array_of_samples(), dtype=np.float64)
        channels = trimmed.channels
        if channels > 1:
            # Use left channel for zero-crossing detection
            samples_mono = samples[::channels]
        else:
            samples_mono = samples

        sr = trimmed.frame_rate
        search_range = 256

        # Snap start
        new_start = find_zero_crossing(samples_mono, 0, search_range=search_range)
        # Snap end
        new_end = find_zero_crossing(samples_mono, len(samples_mono) - 1, search_range=search_range)
        new_end = max(new_end, new_start + 1)

        # Convert sample indices back to ms
        start_trim_ms = int(new_start / sr * 1000)
        end_trim_ms = int(new_end / sr * 1000)
        trimmed = trimmed[start_trim_ms:end_trim_ms]

    if fade_ms > 0 and len(trimmed) > fade_ms * 2:
        trimmed = trimmed.fade_in(fade_ms).fade_out(fade_ms)

    return trimmed


def trim_clip_centered(
    audio_path: str,
    word_start_s: float,
    word_end_s: float,
    clip_duration_s: float,
    out_path: str,
    fade_ms: int = 8,
) -> str:
    """File-level wrapper: load audio, trim centered, export WAV."""
    audio = AudioSegment.from_file(audio_path)
    trimmed = trim_word_centered(
        audio, word_start_s, word_end_s, clip_duration_s, fade_ms=fade_ms,
    )
    trimmed.export(out_path, format="wav")
    return out_path
