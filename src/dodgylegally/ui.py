"""UI module — console output, progress tracking, and step summaries."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field


@dataclass
class StepSummary:
    """Tracks and renders results for a pipeline step."""

    step_name: str
    _successes: list[str] = field(default_factory=list)
    _failures: list[tuple[str, str]] = field(default_factory=list)
    _skips: list[tuple[str, str]] = field(default_factory=list)

    def record_success(self, item: str) -> None:
        self._successes.append(item)

    def record_failure(self, item: str, reason: str) -> None:
        self._failures.append((item, reason))

    def record_skip(self, item: str, reason: str) -> None:
        self._skips.append((item, reason))

    @property
    def succeeded(self) -> int:
        return len(self._successes)

    @property
    def failed(self) -> int:
        return len(self._failures)

    @property
    def skipped(self) -> int:
        return len(self._skips)

    @property
    def total(self) -> int:
        return self.succeeded + self.failed + self.skipped

    def render(self) -> str:
        return (
            f"{self.step_name}: "
            f"{self.succeeded} succeeded, "
            f"{self.failed} failed, "
            f"{self.skipped} skipped "
            f"({self.total} total)"
        )


class Console:
    """Output wrapper that respects quiet/verbose modes."""

    def __init__(self, quiet: bool = False, verbose: bool = False):
        self._quiet = quiet
        self._verbose = verbose

    def info(self, message: str, file=None) -> None:
        if self._quiet:
            return
        dest = file if file is not None else sys.stderr
        print(message, file=dest)

    def error(self, message: str, file=None) -> None:
        dest = file if file is not None else sys.stderr
        print(message, file=dest)

    def debug(self, message: str, file=None) -> None:
        if not self._verbose:
            return
        dest = file if file is not None else sys.stderr
        print(message, file=dest)


@dataclass
class ProgressTracker:
    """Tracks progress through a set of items."""

    total: int
    label: str
    completed: int = 0

    def advance(self) -> None:
        self.completed += 1
