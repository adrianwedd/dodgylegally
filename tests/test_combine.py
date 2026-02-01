import os

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
