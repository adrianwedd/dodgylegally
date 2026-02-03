"""Tests for transcript fetching, VTT parsing, word timestamp search, and STT."""

from unittest.mock import patch, MagicMock

import pytest

from dodgylegally.transcript import (
    CaptionSegment,
    WordSpan,
    parse_vtt,
    find_word_timestamp,
    probe_captions,
    transcribe_and_find,
    transcribe_and_find_all,
)


# --- parse_vtt ---

def test_parse_vtt_well_formed():
    """parse_vtt extracts segments from standard WebVTT content."""
    vtt = (
        "WEBVTT\n"
        "\n"
        "00:00:01.000 --> 00:00:03.500\n"
        "Hello world\n"
        "\n"
        "00:00:05.200 --> 00:00:08.000\n"
        "This is a test\n"
    )
    segments = parse_vtt(vtt)
    assert len(segments) == 2
    assert segments[0] == CaptionSegment(start_s=1.0, end_s=3.5, text="Hello world")
    assert segments[1] == CaptionSegment(start_s=5.2, end_s=8.0, text="This is a test")


def test_parse_vtt_with_html_tags():
    """parse_vtt strips HTML tags from YouTube auto-generated captions."""
    vtt = (
        "WEBVTT\n"
        "\n"
        "00:00:01.000 --> 00:00:03.000\n"
        "<c> confetti</c><c> is</c><c> great</c>\n"
    )
    segments = parse_vtt(vtt)
    assert len(segments) == 1
    assert segments[0].text == "confetti is great"


def test_parse_vtt_multiline_cue():
    """parse_vtt handles cues that span multiple lines."""
    vtt = (
        "WEBVTT\n"
        "\n"
        "00:00:01.000 --> 00:00:04.000\n"
        "First line\n"
        "Second line\n"
    )
    segments = parse_vtt(vtt)
    assert len(segments) == 1
    assert segments[0].text == "First line Second line"


def test_parse_vtt_with_cue_identifiers():
    """parse_vtt handles VTT files that include optional cue identifiers."""
    vtt = (
        "WEBVTT\n"
        "\n"
        "1\n"
        "00:00:01.000 --> 00:00:02.000\n"
        "Hello\n"
        "\n"
        "2\n"
        "00:00:03.000 --> 00:00:04.000\n"
        "World\n"
    )
    segments = parse_vtt(vtt)
    assert len(segments) == 2
    assert segments[0].text == "Hello"
    assert segments[1].text == "World"


def test_parse_vtt_with_positioning():
    """parse_vtt ignores positioning metadata after the timestamp arrow."""
    vtt = (
        "WEBVTT\n"
        "\n"
        "00:00:01.000 --> 00:00:03.000 position:10% align:start\n"
        "Positioned text\n"
    )
    segments = parse_vtt(vtt)
    assert len(segments) == 1
    assert segments[0].start_s == 1.0
    assert segments[0].end_s == 3.0
    assert segments[0].text == "Positioned text"


def test_parse_vtt_empty():
    """parse_vtt returns empty list for VTT with no cues."""
    vtt = "WEBVTT\n\n"
    segments = parse_vtt(vtt)
    assert segments == []


def test_parse_vtt_hours_timestamp():
    """parse_vtt handles timestamps with hours."""
    vtt = (
        "WEBVTT\n"
        "\n"
        "01:02:03.456 --> 01:02:05.789\n"
        "Long video\n"
    )
    segments = parse_vtt(vtt)
    assert len(segments) == 1
    assert segments[0].start_s == pytest.approx(3723.456, abs=0.001)
    assert segments[0].end_s == pytest.approx(3725.789, abs=0.001)


# --- find_word_timestamp ---

def test_find_word_timestamp_exact_match():
    """find_word_timestamp returns start time of segment containing the word."""
    segments = [
        CaptionSegment(start_s=1.0, end_s=3.0, text="hello world"),
        CaptionSegment(start_s=5.0, end_s=7.0, text="confetti is great"),
        CaptionSegment(start_s=9.0, end_s=11.0, text="goodbye"),
    ]
    assert find_word_timestamp(segments, "confetti") == 5.0


def test_find_word_timestamp_case_insensitive():
    """find_word_timestamp matches regardless of case."""
    segments = [
        CaptionSegment(start_s=2.0, end_s=4.0, text="The CONFETTI fell"),
    ]
    assert find_word_timestamp(segments, "confetti") == 2.0
    assert find_word_timestamp(segments, "CONFETTI") == 2.0


def test_find_word_timestamp_returns_none_when_absent():
    """find_word_timestamp returns None when word is not in any segment."""
    segments = [
        CaptionSegment(start_s=1.0, end_s=3.0, text="hello world"),
    ]
    assert find_word_timestamp(segments, "confetti") is None


def test_find_word_timestamp_empty_segments():
    """find_word_timestamp returns None for empty segment list."""
    assert find_word_timestamp([], "confetti") is None


def test_find_word_timestamp_word_boundary():
    """find_word_timestamp does not match partial words."""
    segments = [
        CaptionSegment(start_s=1.0, end_s=3.0, text="the confettied party"),
        CaptionSegment(start_s=5.0, end_s=7.0, text="real confetti here"),
    ]
    # Should NOT match "confettied", should match "confetti" in second segment
    assert find_word_timestamp(segments, "confetti") == 5.0


def test_find_word_timestamp_returns_first_occurrence():
    """find_word_timestamp returns the first segment containing the word."""
    segments = [
        CaptionSegment(start_s=1.0, end_s=3.0, text="first confetti"),
        CaptionSegment(start_s=5.0, end_s=7.0, text="second confetti"),
    ]
    assert find_word_timestamp(segments, "confetti") == 1.0


def test_find_word_timestamp_with_punctuation():
    """find_word_timestamp matches words adjacent to punctuation."""
    segments = [
        CaptionSegment(start_s=3.0, end_s=5.0, text="look, confetti!"),
    ]
    assert find_word_timestamp(segments, "confetti") == 3.0


def test_find_word_timestamp_multi_word_query():
    """find_word_timestamp searches for each word and returns earliest match."""
    segments = [
        CaptionSegment(start_s=1.0, end_s=3.0, text="the rain falls"),
        CaptionSegment(start_s=5.0, end_s=7.0, text="thunder is loud"),
    ]
    # With query "rain thunder", should find "rain" first at 1.0
    assert find_word_timestamp(segments, "rain thunder") == 1.0


# --- fetch_captions ---

@patch("dodgylegally.transcript.YoutubeDL")
def test_fetch_captions_returns_none_when_no_captions(mock_ydl_class):
    """fetch_captions returns None when video has no captions."""
    from dodgylegally.transcript import fetch_captions

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "automatic_captions": {},
        "subtitles": {},
    }
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    result = fetch_captions("https://youtube.com/watch?v=abc")
    assert result is None


@patch("dodgylegally.transcript.YoutubeDL")
def test_fetch_captions_returns_none_when_no_matching_lang(mock_ydl_class):
    """fetch_captions returns None when requested language is unavailable."""
    from dodgylegally.transcript import fetch_captions

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "automatic_captions": {"fr": [{"ext": "vtt", "url": "http://example.com/fr.vtt"}]},
        "subtitles": {},
    }
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    result = fetch_captions("https://youtube.com/watch?v=abc", lang="en")
    assert result is None


@patch("dodgylegally.transcript.urlopen")
@patch("dodgylegally.transcript.YoutubeDL")
def test_fetch_captions_parses_auto_captions(mock_ydl_class, mock_urlopen):
    """fetch_captions downloads and parses auto-generated captions."""
    from dodgylegally.transcript import fetch_captions

    vtt_content = (
        "WEBVTT\n"
        "\n"
        "00:00:01.000 --> 00:00:03.000\n"
        "hello world\n"
    )

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "automatic_captions": {
            "en": [
                {"ext": "vtt", "url": "http://example.com/en.vtt"},
            ],
        },
        "subtitles": {},
    }
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    mock_response = MagicMock()
    mock_response.read.return_value = vtt_content.encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    segments = fetch_captions("https://youtube.com/watch?v=abc")
    assert segments is not None
    assert len(segments) == 1
    assert segments[0].text == "hello world"


@patch("dodgylegally.transcript.urlopen")
@patch("dodgylegally.transcript.YoutubeDL")
def test_fetch_captions_prefers_manual_subs(mock_ydl_class, mock_urlopen):
    """fetch_captions prefers manual subtitles over auto-generated."""
    from dodgylegally.transcript import fetch_captions

    vtt_content = (
        "WEBVTT\n"
        "\n"
        "00:00:02.000 --> 00:00:04.000\n"
        "manual subtitle\n"
    )

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "automatic_captions": {
            "en": [{"ext": "vtt", "url": "http://example.com/auto.vtt"}],
        },
        "subtitles": {
            "en": [{"ext": "vtt", "url": "http://example.com/manual.vtt"}],
        },
    }
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    mock_response = MagicMock()
    mock_response.read.return_value = vtt_content.encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    segments = fetch_captions("https://youtube.com/watch?v=abc")
    # Verify it fetched the manual sub URL, not auto
    mock_urlopen.assert_called_once_with("http://example.com/manual.vtt")


@patch("dodgylegally.transcript.urlopen")
@patch("dodgylegally.transcript.YoutubeDL")
def test_fetch_captions_returns_none_on_download_error(mock_ydl_class, mock_urlopen):
    """fetch_captions returns None when VTT download fails."""
    from dodgylegally.transcript import fetch_captions

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "automatic_captions": {
            "en": [{"ext": "vtt", "url": "http://example.com/en.vtt"}],
        },
        "subtitles": {},
    }
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    mock_urlopen.side_effect = Exception("Network error")

    result = fetch_captions("https://youtube.com/watch?v=abc")
    assert result is None


@patch("dodgylegally.transcript.YoutubeDL")
def test_fetch_captions_returns_none_on_extract_error(mock_ydl_class):
    """fetch_captions returns None when yt-dlp extract_info fails."""
    from dodgylegally.transcript import fetch_captions

    mock_ydl = MagicMock()
    mock_ydl.extract_info.side_effect = Exception("Video unavailable")
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    result = fetch_captions("https://youtube.com/watch?v=abc")
    assert result is None


@patch("dodgylegally.transcript.urlopen")
@patch("dodgylegally.transcript.YoutubeDL")
def test_fetch_captions_picks_vtt_format(mock_ydl_class, mock_urlopen):
    """fetch_captions selects the VTT format from available subtitle formats."""
    from dodgylegally.transcript import fetch_captions

    vtt_content = (
        "WEBVTT\n"
        "\n"
        "00:00:01.000 --> 00:00:02.000\n"
        "test\n"
    )

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "automatic_captions": {
            "en": [
                {"ext": "json3", "url": "http://example.com/en.json3"},
                {"ext": "vtt", "url": "http://example.com/en.vtt"},
                {"ext": "srv1", "url": "http://example.com/en.srv1"},
            ],
        },
        "subtitles": {},
    }
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    mock_response = MagicMock()
    mock_response.read.return_value = vtt_content.encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    segments = fetch_captions("https://youtube.com/watch?v=abc")
    assert segments is not None
    mock_urlopen.assert_called_once_with("http://example.com/en.vtt")


# --- probe_captions ---

@patch("dodgylegally.transcript.find_word_timestamp")
@patch("dodgylegally.transcript.fetch_captions")
def test_probe_captions_returns_timestamp_when_found(mock_fetch, mock_find):
    """probe_captions returns timestamp when word is found in captions."""
    mock_fetch.return_value = [CaptionSegment(start_s=5.0, end_s=7.0, text="confetti")]
    mock_find.return_value = 5.0

    result = probe_captions("https://youtube.com/watch?v=abc", "confetti")
    assert result == 5.0
    mock_fetch.assert_called_once_with("https://youtube.com/watch?v=abc", lang="en")
    mock_find.assert_called_once_with(mock_fetch.return_value, "confetti")


@patch("dodgylegally.transcript.fetch_captions")
def test_probe_captions_returns_none_when_no_captions(mock_fetch):
    """probe_captions returns None when no captions are available."""
    mock_fetch.return_value = None

    result = probe_captions("https://youtube.com/watch?v=abc", "confetti")
    assert result is None


@patch("dodgylegally.transcript.find_word_timestamp")
@patch("dodgylegally.transcript.fetch_captions")
def test_probe_captions_returns_none_when_word_not_found(mock_fetch, mock_find):
    """probe_captions returns None when word is not in captions."""
    mock_fetch.return_value = [CaptionSegment(start_s=1.0, end_s=3.0, text="hello world")]
    mock_find.return_value = None

    result = probe_captions("https://youtube.com/watch?v=abc", "confetti")
    assert result is None


@patch("dodgylegally.transcript.find_word_timestamp")
@patch("dodgylegally.transcript.fetch_captions")
def test_probe_captions_passes_lang(mock_fetch, mock_find):
    """probe_captions passes lang parameter to fetch_captions."""
    mock_fetch.return_value = [CaptionSegment(start_s=1.0, end_s=2.0, text="hola")]
    mock_find.return_value = 1.0

    probe_captions("https://youtube.com/watch?v=abc", "hola", lang="es")
    mock_fetch.assert_called_once_with("https://youtube.com/watch?v=abc", lang="es")


# --- transcribe_and_find ---

@patch("dodgylegally.transcript.WhisperModel", create=True)
def test_transcribe_and_find_word_found(mock_model_cls):
    """transcribe_and_find returns WordSpan when word is found via word_timestamps."""
    mock_word = MagicMock()
    mock_word.word = "confetti"
    mock_word.start = 12.5
    mock_word.end = 13.1

    mock_segment = MagicMock()
    mock_segment.words = [
        MagicMock(word="the", start=12.0, end=12.4),
        mock_word,
    ]
    mock_segment.text = "the confetti"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())
    mock_model_cls.return_value = mock_model

    with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_model_cls)}):
        result = transcribe_and_find("/tmp/audio.wav", "confetti")

    assert isinstance(result, WordSpan)
    assert result.start_s == 12.5
    assert result.end_s == 13.1


@patch("dodgylegally.transcript.WhisperModel", create=True)
def test_transcribe_and_find_word_not_found(mock_model_cls):
    """transcribe_and_find returns None when word is not in transcript."""
    mock_segment = MagicMock()
    mock_segment.words = [MagicMock(word="hello", start=1.0)]
    mock_segment.text = "hello"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())
    mock_model_cls.return_value = mock_model

    with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_model_cls)}):
        result = transcribe_and_find("/tmp/audio.wav", "confetti")

    assert result is None


def test_transcribe_and_find_no_whisper_installed():
    """transcribe_and_find returns None when faster-whisper is not installed."""
    import sys
    # Temporarily remove faster_whisper from modules if present
    saved = sys.modules.pop("faster_whisper", None)
    try:
        with patch.dict("sys.modules", {"faster_whisper": None}):
            result = transcribe_and_find("/tmp/audio.wav", "confetti")
        assert result is None
    finally:
        if saved is not None:
            sys.modules["faster_whisper"] = saved


@patch("dodgylegally.transcript.WhisperModel", create=True)
def test_transcribe_and_find_multi_word_returns_full_span(mock_model_cls):
    """transcribe_and_find returns WordSpan covering all words of multi-word query."""
    mock_words = [
        MagicMock(word="rain", start=3.0, end=3.4),
        MagicMock(word="thunder", start=3.5, end=4.1),
    ]

    mock_segment = MagicMock()
    mock_segment.words = mock_words
    mock_segment.text = "rain thunder"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())
    mock_model_cls.return_value = mock_model

    with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_model_cls)}):
        result = transcribe_and_find("/tmp/audio.wav", "rain thunder")

    assert isinstance(result, WordSpan)
    assert result.start_s == 3.0
    assert result.end_s == 4.1


@patch("dodgylegally.transcript.WhisperModel", create=True)
def test_transcribe_and_find_segment_text_fallback(mock_model_cls):
    """transcribe_and_find falls back to segment.text with estimated end when words is empty."""
    mock_segment = MagicMock()
    mock_segment.words = []
    mock_segment.text = "the confetti flew"
    mock_segment.start = 7.0

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())
    mock_model_cls.return_value = mock_model

    with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_model_cls)}):
        result = transcribe_and_find("/tmp/audio.wav", "confetti")

    assert isinstance(result, WordSpan)
    assert result.start_s == 7.0
    assert result.end_s == pytest.approx(7.3)


@patch("dodgylegally.transcript.WhisperModel", create=True)
def test_transcribe_and_find_passes_model_size(mock_model_cls):
    """transcribe_and_find passes model_size to WhisperModel."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([]), MagicMock())
    mock_model_cls.return_value = mock_model

    with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_model_cls)}):
        transcribe_and_find("/tmp/audio.wav", "test", model_size="tiny")

    mock_model_cls.assert_called_once_with("tiny", compute_type="int8")


# --- WordSpan ---

def test_word_span_dataclass_fields():
    """WordSpan holds start_s and end_s timestamps."""
    span = WordSpan(start_s=1.5, end_s=2.3)
    assert span.start_s == 1.5
    assert span.end_s == 2.3


@patch("dodgylegally.transcript.WhisperModel", create=True)
def test_transcribe_and_find_multi_word_spread_across_segments(mock_model_cls):
    """transcribe_and_find finds multi-word phrase spread near each other."""
    # "tornado full of" — words within 3s window
    mock_seg1 = MagicMock()
    mock_seg1.words = [
        MagicMock(word="a", start=1.0, end=1.2),
        MagicMock(word="tornado", start=1.3, end=1.9),
        MagicMock(word="full", start=2.0, end=2.3),
        MagicMock(word="of", start=2.4, end=2.5),
        MagicMock(word="confetti", start=2.6, end=3.1),
    ]
    mock_seg1.text = "a tornado full of confetti"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_seg1]), MagicMock())
    mock_model_cls.return_value = mock_model

    with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_model_cls)}):
        result = transcribe_and_find("/tmp/audio.wav", "tornado full of")

    assert isinstance(result, WordSpan)
    assert result.start_s == 1.3
    assert result.end_s == 2.5


# --- transcribe_and_find with model param ---

def test_transcribe_and_find_accepts_model_param():
    """transcribe_and_find uses a pre-loaded model when provided."""
    mock_word = MagicMock()
    mock_word.word = "confetti"
    mock_word.start = 5.0
    mock_word.end = 5.6

    mock_segment = MagicMock()
    mock_segment.words = [mock_word]
    mock_segment.text = "confetti"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())

    result = transcribe_and_find("/tmp/audio.wav", "confetti", model=mock_model)

    assert isinstance(result, WordSpan)
    assert result.start_s == 5.0
    assert result.end_s == 5.6
    mock_model.transcribe.assert_called_once_with("/tmp/audio.wav", word_timestamps=True)


# --- transcribe_and_find_all ---

def test_transcribe_and_find_all_returns_list():
    """transcribe_and_find_all returns all occurrences of the word."""
    mock_words = [
        MagicMock(word="confetti", start=2.0, end=2.5),
        MagicMock(word="is", start=2.6, end=2.8),
        MagicMock(word="confetti", start=7.0, end=7.4),
    ]

    mock_segment = MagicMock()
    mock_segment.words = mock_words
    mock_segment.text = "confetti is confetti"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())

    result = transcribe_and_find_all("/tmp/audio.wav", "confetti", model=mock_model)

    assert len(result) == 2
    assert result[0] == WordSpan(start_s=2.0, end_s=2.5)
    assert result[1] == WordSpan(start_s=7.0, end_s=7.4)


def test_transcribe_and_find_all_empty():
    """transcribe_and_find_all returns empty list when word not found."""
    mock_segment = MagicMock()
    mock_segment.words = [MagicMock(word="hello", start=1.0, end=1.3)]
    mock_segment.text = "hello"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())

    result = transcribe_and_find_all("/tmp/audio.wav", "confetti", model=mock_model)

    assert result == []


def test_transcribe_and_find_all_multi_word():
    """transcribe_and_find_all returns all occurrences of a multi-word phrase."""
    mock_words = [
        MagicMock(word="full", start=1.0, end=1.2),
        MagicMock(word="of", start=1.3, end=1.4),
        MagicMock(word="stuff", start=1.5, end=1.8),
        MagicMock(word="and", start=5.0, end=5.2),
        MagicMock(word="full", start=5.3, end=5.5),
        MagicMock(word="of", start=5.6, end=5.7),
        MagicMock(word="things", start=5.8, end=6.1),
    ]

    mock_segment = MagicMock()
    mock_segment.words = mock_words
    mock_segment.text = "full of stuff and full of things"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())

    result = transcribe_and_find_all("/tmp/audio.wav", "full of", model=mock_model)

    assert len(result) == 2
    assert result[0] == WordSpan(start_s=1.0, end_s=1.4)
    assert result[1] == WordSpan(start_s=5.3, end_s=5.7)


def test_transcribe_and_find_all_no_whisper():
    """transcribe_and_find_all returns empty list when whisper unavailable."""
    import sys
    saved = sys.modules.pop("faster_whisper", None)
    try:
        with patch.dict("sys.modules", {"faster_whisper": None}):
            result = transcribe_and_find_all("/tmp/audio.wav", "confetti")
        assert result == []
    finally:
        if saved is not None:
            sys.modules["faster_whisper"] = saved
