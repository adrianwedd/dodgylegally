"""Tests for the clip extraction module."""

from unittest.mock import patch

import pytest

from dodgylegally.clip import ClipPosition, ClipSpec, DownloadRangeFunc, DEFAULT_CLIP_SPEC


class TestClipPosition:
    def test_from_string_midpoint(self):
        assert ClipPosition.from_string("midpoint") is ClipPosition.MIDPOINT

    def test_from_string_random(self):
        assert ClipPosition.from_string("random") is ClipPosition.RANDOM

    def test_from_string_timestamp(self):
        pos = ClipPosition.from_string("30.5")
        assert pos is ClipPosition.TIMESTAMP

    def test_from_string_integer_timestamp(self):
        pos = ClipPosition.from_string("0")
        assert pos is ClipPosition.TIMESTAMP

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid clip position"):
            ClipPosition.from_string("bogus")

    def test_from_string_negative(self):
        with pytest.raises(ValueError, match="Invalid clip position"):
            ClipPosition.from_string("-5")


class TestClipSpec:
    def test_default_matches_legacy(self):
        """Default spec = midpoint, 1 second — matches original behavior."""
        spec = ClipSpec()
        assert spec.position is ClipPosition.MIDPOINT
        assert spec.duration_s == 1.0
        assert spec.timestamp_s is None

    def test_default_constant(self):
        assert DEFAULT_CLIP_SPEC.position is ClipPosition.MIDPOINT
        assert DEFAULT_CLIP_SPEC.duration_s == 1.0

    def test_duration_must_be_positive(self):
        with pytest.raises(ValueError, match="duration_s must be positive"):
            ClipSpec(duration_s=0)

    def test_duration_negative_rejected(self):
        with pytest.raises(ValueError, match="duration_s must be positive"):
            ClipSpec(duration_s=-1.0)

    def test_timestamp_requires_timestamp_position(self):
        with pytest.raises(ValueError, match="timestamp_s required"):
            ClipSpec(position=ClipPosition.TIMESTAMP, timestamp_s=None)

    def test_timestamp_must_be_non_negative(self):
        with pytest.raises(ValueError, match="timestamp_s must be non-negative"):
            ClipSpec(position=ClipPosition.TIMESTAMP, timestamp_s=-1.0)

    def test_from_cli_midpoint(self):
        spec = ClipSpec.from_cli("midpoint", 1.0)
        assert spec.position is ClipPosition.MIDPOINT
        assert spec.duration_s == 1.0

    def test_from_cli_random(self):
        spec = ClipSpec.from_cli("random", 2.0)
        assert spec.position is ClipPosition.RANDOM
        assert spec.duration_s == 2.0

    def test_from_cli_timestamp(self):
        spec = ClipSpec.from_cli("30.5", 1.5)
        assert spec.position is ClipPosition.TIMESTAMP
        assert spec.timestamp_s == 30.5
        assert spec.duration_s == 1.5

    def test_from_cli_zero_timestamp(self):
        spec = ClipSpec.from_cli("0", 1.0)
        assert spec.position is ClipPosition.TIMESTAMP
        assert spec.timestamp_s == 0.0


class TestComputeStartTime:
    def test_midpoint_computes_center(self):
        spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.0)
        start = spec.compute_start_time(total_duration_s=100.0)
        assert start == 49.5  # center of 100s minus half of 1s

    def test_midpoint_short_source(self):
        """When source is shorter than clip, start at 0."""
        spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=2.0)
        start = spec.compute_start_time(total_duration_s=1.0)
        assert start == 0.0

    def test_midpoint_no_duration(self):
        """When total duration unknown, start at 0."""
        spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.0)
        start = spec.compute_start_time(total_duration_s=None)
        assert start == 0.0

    def test_random_within_margins(self):
        """Random position stays within 5%-95% of source, avoiding intros/outros."""
        spec = ClipSpec(position=ClipPosition.RANDOM, duration_s=1.0)
        for _ in range(100):
            start = spec.compute_start_time(total_duration_s=100.0)
            assert start >= 5.0   # 5% of 100
            assert start <= 94.0  # 95% of 100 minus 1s clip

    def test_random_short_source(self):
        """When source is too short for margins, fall back to 0."""
        spec = ClipSpec(position=ClipPosition.RANDOM, duration_s=1.0)
        start = spec.compute_start_time(total_duration_s=1.5)
        assert start >= 0.0
        assert start <= 0.5

    def test_random_no_duration(self):
        spec = ClipSpec(position=ClipPosition.RANDOM, duration_s=1.0)
        start = spec.compute_start_time(total_duration_s=None)
        assert start == 0.0

    def test_timestamp_returns_requested(self):
        spec = ClipSpec(position=ClipPosition.TIMESTAMP, timestamp_s=30.0, duration_s=1.0)
        start = spec.compute_start_time(total_duration_s=100.0)
        assert start == 30.0

    def test_timestamp_clamps_near_end(self):
        """Timestamp near end of source gets clamped so clip doesn't exceed."""
        spec = ClipSpec(position=ClipPosition.TIMESTAMP, timestamp_s=99.5, duration_s=1.0)
        start = spec.compute_start_time(total_duration_s=100.0)
        assert start == 99.0  # clamped: 100 - 1

    def test_timestamp_beyond_source(self):
        """Timestamp past source duration clamps to end."""
        spec = ClipSpec(position=ClipPosition.TIMESTAMP, timestamp_s=200.0, duration_s=1.0)
        start = spec.compute_start_time(total_duration_s=100.0)
        assert start == 99.0

    def test_timestamp_no_duration(self):
        """When total duration unknown, use timestamp directly."""
        spec = ClipSpec(position=ClipPosition.TIMESTAMP, timestamp_s=30.0, duration_s=1.0)
        start = spec.compute_start_time(total_duration_s=None)
        assert start == 30.0


class TestDownloadRangeFunc:
    def test_default_spec_matches_legacy(self):
        """Default DownloadRangeFunc behaves exactly like old _DownloadRangeFunc."""
        func = DownloadRangeFunc()
        result = list(func({"duration": 100}, None))
        assert len(result) == 1
        assert result[0]["start_time"] == 49.5
        assert result[0]["end_time"] == 50.5

    def test_custom_duration(self):
        spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=2.0)
        func = DownloadRangeFunc(spec=spec)
        result = list(func({"duration": 100}, None))
        assert result[0]["start_time"] == 49.0
        assert result[0]["end_time"] == 51.0

    def test_random_position(self):
        spec = ClipSpec(position=ClipPosition.RANDOM, duration_s=1.0)
        func = DownloadRangeFunc(spec=spec)
        result = list(func({"duration": 100}, None))
        assert len(result) == 1
        assert result[0]["start_time"] >= 5.0
        assert result[0]["end_time"] <= 96.0

    def test_timestamp_position(self):
        spec = ClipSpec(position=ClipPosition.TIMESTAMP, timestamp_s=30.0, duration_s=1.0)
        func = DownloadRangeFunc(spec=spec)
        result = list(func({"duration": 100}, None))
        assert result[0]["start_time"] == 30.0
        assert result[0]["end_time"] == 31.0

    def test_no_duration_in_info(self):
        func = DownloadRangeFunc()
        result = list(func({"duration": None}, None))
        assert result[0]["start_time"] == 0
        assert result[0]["end_time"] == 1.0

    def test_missing_duration_key(self):
        func = DownloadRangeFunc()
        result = list(func({}, None))
        assert result[0]["start_time"] == 0
        assert result[0]["end_time"] == 1.0
