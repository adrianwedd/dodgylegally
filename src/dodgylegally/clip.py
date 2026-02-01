"""Clip extraction position and duration configuration."""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass


class ClipPosition(enum.Enum):
    """Where in the source audio to extract the clip."""

    MIDPOINT = "midpoint"
    RANDOM = "random"
    TIMESTAMP = "timestamp"

    @classmethod
    def from_string(cls, value: str) -> ClipPosition:
        """Parse a CLI string into a ClipPosition.

        Accepts 'midpoint', 'random', or a non-negative number (timestamp).
        """
        if value == "midpoint":
            return cls.MIDPOINT
        if value == "random":
            return cls.RANDOM
        try:
            ts = float(value)
            if ts < 0:
                raise ValueError
            return cls.TIMESTAMP
        except ValueError:
            raise ValueError(
                f"Invalid clip position: '{value}'. "
                "Use 'midpoint', 'random', or a non-negative number of seconds."
            )


@dataclass(frozen=True)
class ClipSpec:
    """Specifies where and how long to extract a clip from source audio."""

    position: ClipPosition = ClipPosition.MIDPOINT
    duration_s: float = 1.0
    timestamp_s: float | None = None

    def __post_init__(self):
        if self.duration_s <= 0:
            raise ValueError(f"duration_s must be positive, got {self.duration_s}")
        if self.position is ClipPosition.TIMESTAMP:
            if self.timestamp_s is None:
                raise ValueError("timestamp_s required when position is TIMESTAMP")
            if self.timestamp_s < 0:
                raise ValueError(f"timestamp_s must be non-negative, got {self.timestamp_s}")

    @classmethod
    def from_cli(cls, position_str: str, duration_s: float) -> ClipSpec:
        """Build a ClipSpec from CLI flag values."""
        pos = ClipPosition.from_string(position_str)
        timestamp_s = None
        if pos is ClipPosition.TIMESTAMP:
            timestamp_s = float(position_str)
        return cls(position=pos, duration_s=duration_s, timestamp_s=timestamp_s)

    def compute_start_time(self, total_duration_s: float | None) -> float:
        """Compute the start time in seconds for clip extraction.

        Args:
            total_duration_s: Total source duration in seconds, or None if unknown.

        Returns:
            Start time in seconds.
        """
        if total_duration_s is None:
            if self.position is ClipPosition.TIMESTAMP:
                return self.timestamp_s
            return 0.0

        if self.position is ClipPosition.MIDPOINT:
            start = (total_duration_s - self.duration_s) / 2
            return max(start, 0.0)

        if self.position is ClipPosition.RANDOM:
            margin = total_duration_s * 0.05
            earliest = margin
            latest = total_duration_s - margin - self.duration_s
            if latest <= earliest:
                # Source too short for margins — use full range
                latest = max(total_duration_s - self.duration_s, 0.0)
                earliest = 0.0
            return random.uniform(earliest, max(earliest, latest))

        # TIMESTAMP
        max_start = total_duration_s - self.duration_s
        return min(self.timestamp_s, max(max_start, 0.0))


DEFAULT_CLIP_SPEC = ClipSpec()


class DownloadRangeFunc:
    """yt-dlp download_ranges callback that uses ClipSpec for positioning."""

    def __init__(self, spec: ClipSpec | None = None):
        self._spec = spec or DEFAULT_CLIP_SPEC

    def __call__(self, info_dict, ydl):
        duration = info_dict.get("duration")
        start = self._spec.compute_start_time(duration)
        yield {"start_time": start, "end_time": start + self._spec.duration_s}
