import os

from pydub import AudioSegment
from pydub.generators import WhiteNoise

from dodgylegally.process import make_oneshot, make_loop, process_file, trim_word_centered, trim_clip_centered


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


def test_process_file_with_effect_chain(tmp_path):
    """process_file applies effect chain and produces output files."""
    from dodgylegally.effects import parse_chain

    src = _make_test_wav(str(tmp_path / "input.wav"))
    oneshot_dir = str(tmp_path / "oneshot")
    loop_dir = str(tmp_path / "loop")
    os.makedirs(oneshot_dir)
    os.makedirs(loop_dir)
    chain = parse_chain("reverse")
    result = process_file(src, oneshot_dir, loop_dir, effect_chain=chain)
    assert result is not None
    assert os.path.exists(result[0])
    assert os.path.exists(result[1])


def test_process_file_effect_chain_cleans_tempfile(tmp_path):
    """process_file with effect chain does not leak temp files."""
    import tempfile
    from dodgylegally.effects import parse_chain

    src = _make_test_wav(str(tmp_path / "input.wav"))
    oneshot_dir = str(tmp_path / "oneshot")
    loop_dir = str(tmp_path / "loop")
    os.makedirs(oneshot_dir)
    os.makedirs(loop_dir)
    chain = parse_chain("reverse")

    temp_dir = tempfile.gettempdir()
    before = set(os.listdir(temp_dir))
    process_file(src, oneshot_dir, loop_dir, effect_chain=chain)
    after = set(os.listdir(temp_dir))
    new_wav_files = [f for f in (after - before) if f.endswith(".wav")]
    assert len(new_wav_files) == 0, f"Leaked temp files: {new_wav_files}"


def test_process_file_skips_short_audio(tmp_path):
    src = _make_test_wav(str(tmp_path / "input.wav"), duration_ms=200)
    oneshot_dir = str(tmp_path / "oneshot")
    loop_dir = str(tmp_path / "loop")
    os.makedirs(oneshot_dir)
    os.makedirs(loop_dir)
    result = process_file(src, oneshot_dir, loop_dir)
    assert result is None


# --- trim_word_centered ---

def test_trim_word_centered_centers_word():
    """trim_word_centered places word at clip center."""
    # 10s audio, word at 5.0-5.5s, clip duration 2.0s
    # Word midpoint = 5.25s, clip should be ~4.25s to ~6.25s
    audio = WhiteNoise().to_audio_segment(duration=10000)
    result = trim_word_centered(audio, 5.0, 5.5, clip_duration_s=2.0, zero_cross=False)
    assert abs(len(result) - 2000) <= 20  # within 20ms tolerance


def test_trim_word_centered_clamp_start():
    """trim_word_centered clamps when word is near audio start."""
    # Word at 0.1-0.2s in 10s audio, clip duration 2.0s
    # Midpoint = 0.15s, desired start = -0.85s → clamped to 0
    audio = WhiteNoise().to_audio_segment(duration=10000)
    result = trim_word_centered(audio, 0.1, 0.2, clip_duration_s=2.0, zero_cross=False)
    assert abs(len(result) - 2000) <= 20


def test_trim_word_centered_clamp_end():
    """trim_word_centered clamps when word is near audio end."""
    # Word at 9.7-9.9s in 10s audio, clip duration 2.0s
    audio = WhiteNoise().to_audio_segment(duration=10000)
    result = trim_word_centered(audio, 9.7, 9.9, clip_duration_s=2.0, zero_cross=False)
    assert abs(len(result) - 2000) <= 20


def test_trim_word_centered_applies_fades():
    """trim_word_centered applies micro-fades at edges."""
    import numpy as np
    audio = WhiteNoise().to_audio_segment(duration=5000)
    result = trim_word_centered(audio, 2.0, 2.5, clip_duration_s=1.0, fade_ms=50, zero_cross=False)
    # Check that first and last samples are attenuated relative to interior
    samples = np.array(result.get_array_of_samples(), dtype=np.float64)
    # First few samples should be near zero (faded in)
    assert abs(samples[0]) < abs(samples[len(samples) // 2]) or samples[0] == 0


def test_trim_word_centered_no_zero_cross():
    """trim_word_centered works with zero_cross=False."""
    audio = WhiteNoise().to_audio_segment(duration=5000)
    result = trim_word_centered(audio, 2.0, 2.5, clip_duration_s=1.0, zero_cross=False)
    assert len(result) > 0


# --- trim_word_centered word-boundary mode (clip_duration_s=0) ---

def test_trim_word_boundary_mode_length():
    """clip_duration_s=0 trims to word span + 2×pad."""
    # 10s audio, word at 3.0-3.5s (500ms word), default pad=50ms
    # Expected length: ~600ms (500ms + 2×50ms), give or take zero-crossing
    audio = WhiteNoise().to_audio_segment(duration=10000)
    result = trim_word_centered(audio, 3.0, 3.5, clip_duration_s=0, zero_cross=False)
    assert abs(len(result) - 600) <= 20


def test_trim_word_boundary_custom_pad():
    """clip_duration_s=0 with custom pad_ms."""
    audio = WhiteNoise().to_audio_segment(duration=10000)
    result = trim_word_centered(audio, 3.0, 3.5, clip_duration_s=0, pad_ms=100, zero_cross=False)
    # 500ms word + 2×100ms pad = 700ms
    assert abs(len(result) - 700) <= 20


def test_trim_word_boundary_zero_crossing():
    """clip_duration_s=0 still applies zero-crossing snap."""
    audio = WhiteNoise().to_audio_segment(duration=10000)
    result = trim_word_centered(audio, 3.0, 3.5, clip_duration_s=0, zero_cross=True)
    # Should be close to 600ms but may vary due to zero-crossing snap
    assert 400 <= len(result) <= 800


def test_trim_word_boundary_applies_fades():
    """clip_duration_s=0 applies micro-fades."""
    import numpy as np
    audio = WhiteNoise().to_audio_segment(duration=10000)
    result = trim_word_centered(audio, 3.0, 3.5, clip_duration_s=0, fade_ms=50, zero_cross=False)
    samples = np.array(result.get_array_of_samples(), dtype=np.float64)
    # First sample should be attenuated (faded in)
    assert abs(samples[0]) < abs(samples[len(samples) // 2]) or samples[0] == 0


def test_trim_word_boundary_clamp_start():
    """clip_duration_s=0 clamps when word is at audio start."""
    # Word starts at 0.01s, pad would go to -0.04s → clamped to 0
    audio = WhiteNoise().to_audio_segment(duration=5000)
    result = trim_word_centered(audio, 0.01, 0.3, clip_duration_s=0, zero_cross=False)
    assert len(result) > 0
    # Should be roughly 340ms (word 290ms + one-sided pad + clamped start)
    assert len(result) <= 400


def test_trim_word_boundary_clamp_end():
    """clip_duration_s=0 clamps when word is at audio end."""
    audio = WhiteNoise().to_audio_segment(duration=5000)
    # Word at 4.8-4.99s, pad would extend past 5.0s
    result = trim_word_centered(audio, 4.8, 4.99, clip_duration_s=0, zero_cross=False)
    assert len(result) > 0
    assert len(result) <= 300


def test_trim_clip_centered_writes_wav(tmp_path):
    """trim_clip_centered writes a valid WAV file."""
    src = str(tmp_path / "input.wav")
    out = str(tmp_path / "output.wav")
    WhiteNoise().to_audio_segment(duration=5000).export(src, format="wav")
    result = trim_clip_centered(src, 2.0, 2.5, clip_duration_s=1.0, out_path=out)
    assert os.path.exists(result)
    written = AudioSegment.from_file(result)
    assert abs(len(written) - 1000) <= 20
