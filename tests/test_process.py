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
