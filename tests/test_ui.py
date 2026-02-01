"""Tests for the ui module — rich console wrappers for progress and feedback."""

import io
from unittest.mock import patch

import pytest


def test_step_summary_formats_counts():
    """StepSummary formats download/process/combine results as a table."""
    from dodgylegally.ui import StepSummary

    summary = StepSummary("Download")
    summary.record_success("file1.wav")
    summary.record_success("file2.wav")
    summary.record_failure("phrase3", "rate limited")
    summary.record_skip("phrase4", "no results")

    assert summary.succeeded == 2
    assert summary.failed == 1
    assert summary.skipped == 1
    assert summary.total == 4


def test_step_summary_render_contains_counts():
    """Rendered summary string contains the step name and counts."""
    from dodgylegally.ui import StepSummary

    summary = StepSummary("Process")
    summary.record_success("a.wav")
    summary.record_failure("b.wav", "too short")

    rendered = summary.render()
    assert "Process" in rendered
    assert "1" in rendered  # succeeded
    assert "1" in rendered  # failed


def test_step_summary_empty():
    """Empty summary still renders without error."""
    from dodgylegally.ui import StepSummary

    summary = StepSummary("Combine")
    assert summary.total == 0
    rendered = summary.render()
    assert "Combine" in rendered


def test_console_output_respects_quiet_mode():
    """In quiet mode, info messages are suppressed."""
    from dodgylegally.ui import Console

    console = Console(quiet=True)
    with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
        console.info("this should not appear")
        assert mock_stderr.getvalue() == ""


def test_console_output_shows_info_by_default():
    """By default, info messages are shown."""
    from dodgylegally.ui import Console

    console = Console(quiet=False)
    output = io.StringIO()
    console.info("hello world", file=output)
    assert "hello world" in output.getvalue()


def test_console_error_always_shows():
    """Error messages show even in quiet mode."""
    from dodgylegally.ui import Console

    console = Console(quiet=True)
    output = io.StringIO()
    console.error("something broke", file=output)
    assert "something broke" in output.getvalue()


def test_console_verbose_suppressed_by_default():
    """Verbose/debug messages are hidden unless verbose=True."""
    from dodgylegally.ui import Console

    console = Console(verbose=False)
    output = io.StringIO()
    console.debug("debug info", file=output)
    assert output.getvalue() == ""


def test_console_verbose_shown_when_enabled():
    """Verbose messages show when verbose=True."""
    from dodgylegally.ui import Console

    console = Console(verbose=True)
    output = io.StringIO()
    console.debug("debug info", file=output)
    assert "debug info" in output.getvalue()


def test_progress_tracker_counts():
    """ProgressTracker tracks completed and total items."""
    from dodgylegally.ui import ProgressTracker

    tracker = ProgressTracker(total=5, label="Downloading")
    assert tracker.completed == 0
    assert tracker.total == 5
    tracker.advance()
    tracker.advance()
    assert tracker.completed == 2
