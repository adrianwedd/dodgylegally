#!/usr/bin/env python3
"""Reverse Reveal — the phrase emerges from a wash of reversed audio.

Takes 8 assembled versions, reverses them, layers them as a dense lowpassed
texture with random offsets. At the midpoint, forward (unreversed) versions
begin entering one at a time — dry and centered — cutting through the wash.
The reversed layer fades out and only the forward voices remain, delay tails
dying into silence.

Output: tornado_compositions/reverse_reveal.wav (~20s)
"""

from __future__ import annotations

import json
import os
import random

import numpy as np
from pydub import AudioSegment


BASE = os.path.dirname(os.path.abspath(__file__))
ASSEMBLED_DIR = os.path.join(BASE, "tornado_assembled_supertight_v2")
MANIFEST = os.path.join(ASSEMBLED_DIR, "manifest.json")
OUTPUT_DIR = os.path.join(BASE, "tornado_compositions")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "reverse_reveal.wav")

SAMPLE_RATE = 44100
TOTAL_DURATION_MS = 20000
MIDPOINT_MS = 8000


def lowpass_simple(audio: AudioSegment, cutoff_hz: int = 1200) -> AudioSegment:
    """Simple lowpass via pydub's low_pass_filter."""
    return audio.low_pass_filter(cutoff_hz)


def apply_simple_delay(audio: AudioSegment, delay_ms: int = 250,
                       feedback: float = 0.3, repeats: int = 3) -> AudioSegment:
    """Apply a simple delay effect by overlaying quieter copies."""
    result = audio
    for i in range(1, repeats + 1):
        delayed = AudioSegment.silent(duration=delay_ms * i) + audio
        gain_reduction = -6.0 * i * (1.0 / (feedback + 0.01))
        gain_reduction = max(gain_reduction, -30.0)
        delayed = delayed.apply_gain(gain_reduction)
        # Extend result if needed
        if len(delayed) > len(result):
            result = result + AudioSegment.silent(duration=len(delayed) - len(result))
        result = result.overlay(delayed)
    return result


def main():
    random.seed(42)

    with open(MANIFEST) as f:
        manifest = json.load(f)

    # Use first 8 for reversed wash, next 8 for forward reveal
    reversed_entries = manifest[:8]
    forward_entries = manifest[4:12]  # overlap gives timbral variety

    print("Reverse Reveal")
    print(f"  Reversed wash: {len(reversed_entries)} versions")
    print(f"  Forward reveal: {len(forward_entries)} versions")

    # --- Build the reversed wash layer ---
    wash = AudioSegment.silent(duration=TOTAL_DURATION_MS, frame_rate=SAMPLE_RATE)

    for entry in reversed_entries:
        path = os.path.join(ASSEMBLED_DIR, entry["filename"])
        if not os.path.exists(path):
            continue

        audio = AudioSegment.from_file(path, format="wav")
        reversed_audio = audio.reverse()
        reversed_audio = lowpass_simple(reversed_audio, cutoff_hz=1200)

        # Normalize
        if reversed_audio.dBFS > -80:
            reversed_audio = reversed_audio.apply_gain(-20.0 - reversed_audio.dBFS)

        # Place at random offset within the first 2 seconds (dense cluster)
        offset_ms = random.randint(0, 2000)

        # Layer it twice for density — second copy slightly later
        wash = wash.overlay(reversed_audio, position=offset_ms)
        offset2 = offset_ms + random.randint(300, 1200)
        wash = wash.overlay(reversed_audio.apply_gain(-3.0), position=offset2)

    # Fade the wash: full volume until midpoint, then fade out over 6s
    # Split wash into pre-midpoint and post-midpoint
    wash_pre = wash[:MIDPOINT_MS]
    wash_post = wash[MIDPOINT_MS:]
    wash_post = wash_post.fade_out(6000)
    wash = wash_pre + wash_post

    # --- Build the forward reveal layer ---
    reveal = AudioSegment.silent(duration=TOTAL_DURATION_MS, frame_rate=SAMPLE_RATE)

    # Forward versions enter starting at midpoint, spaced ~1.5s apart
    entry_time_ms = MIDPOINT_MS
    entry_spacing_ms = 1500

    for i, entry in enumerate(forward_entries):
        path = os.path.join(ASSEMBLED_DIR, entry["filename"])
        if not os.path.exists(path):
            continue

        audio = AudioSegment.from_file(path, format="wav")

        # Normalize
        if audio.dBFS > -80:
            audio = audio.apply_gain(-16.0 - audio.dBFS)

        # Add subtle delay tail to first few entries, dry for later ones
        if i < 4:
            audio = apply_simple_delay(audio, delay_ms=200 + i * 50,
                                       feedback=0.25, repeats=2)

        # Fade in the first forward entry gently
        if i == 0:
            audio = audio.fade_in(200)

        if entry_time_ms + len(audio) <= TOTAL_DURATION_MS:
            reveal = reveal.overlay(audio, position=entry_time_ms)
            print(f"  Forward entry at {entry_time_ms / 1000:.1f}s: {entry['filename']}")

        entry_time_ms += entry_spacing_ms

    # --- Mix wash + reveal ---
    # Wash is slightly louder in the first half, reveal dominates second half
    result = wash.overlay(reveal)

    # Master fade-out for clean ending
    result = result.fade_out(2000)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result.export(OUTPUT_FILE, format="wav")
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"Duration: {len(result) / 1000:.1f}s")


if __name__ == "__main__":
    main()
