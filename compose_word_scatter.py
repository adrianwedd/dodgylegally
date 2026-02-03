#!/usr/bin/env python3
"""Word Scatter — individual words extracted and resequenced on a rhythmic grid.

From the 20 assembled versions, extracts individual word clips by going back
to the source files referenced in the manifest. Creates three pools — tornado,
"full of", confetti — and scatters them on a timeline: tornados on beat 1,
"full of" on beat 2, confetti on beat 3, with random omissions and timing
jitter (+/-50ms). Some words get pitch-shifted +/-2 semitones for movement.

8 bars at 90 BPM (~21s).

Output: tornado_compositions/word_scatter.wav
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
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "word_scatter.wav")

BPM = 90
BEATS_PER_BAR = 4
BARS = 8
JITTER_MS = 50
SAMPLE_RATE = 44100


def beat_to_ms(beat: float) -> int:
    """Convert a beat number to milliseconds at the global BPM."""
    return int(beat * 60000 / BPM)


def pitch_shift_audio(audio: AudioSegment, semitones: int) -> AudioSegment:
    """Simple pitch shift via sample rate manipulation.

    Changes pitch by resampling — shifts both pitch and tempo,
    which for short spoken words creates a natural effect.
    """
    if semitones == 0:
        return audio

    factor = 2 ** (semitones / 12.0)
    new_rate = int(audio.frame_rate * factor)

    # Change the frame rate (speeds up / slows down + shifts pitch)
    shifted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
    # Resample back to original rate to restore duration-ish
    shifted = shifted.set_frame_rate(audio.frame_rate)
    return shifted


def load_source_clip(source_path: str) -> AudioSegment | None:
    """Load a source clip, trying several path resolutions."""
    # The manifest stores relative paths from the repo root
    candidates = [
        os.path.join(BASE, source_path),
        source_path,
    ]
    for path in candidates:
        if os.path.exists(path):
            return AudioSegment.from_file(path, format="wav")
    return None


def extract_word_region(audio: AudioSegment, word_dur_ms: int,
                        pad_ms: int = 40) -> AudioSegment:
    """Extract the word region from a clip.

    For source clips that are already word-centered (super_tight variants),
    the word occupies most of the clip. We take the center portion matching
    word_dur_ms plus padding, with micro-fades.
    """
    total_ms = len(audio)
    word_ms = min(word_dur_ms + pad_ms * 2, total_ms)

    # Center-extract
    start = max(0, (total_ms - word_ms) // 2)
    end = min(total_ms, start + word_ms)
    trimmed = audio[start:end]

    # Micro-fades
    fade_ms = min(8, max(1, len(trimmed) // 6))
    trimmed = trimmed.fade_in(fade_ms).fade_out(fade_ms)

    return trimmed


def main():
    random.seed(42)

    with open(MANIFEST) as f:
        manifest = json.load(f)

    # Build word pools from manifest source clips
    pools: dict[str, list[AudioSegment]] = {
        "tornado": [],
        "full of": [],
        "confetti": [],
    }

    print("Word Scatter — extracting individual words from source clips")

    for entry in manifest:
        for clip_info in entry["clips"]:
            word = clip_info["word"]
            source = clip_info["source"]
            word_dur = clip_info["word_dur_ms"]

            audio = load_source_clip(source)
            if audio is None:
                print(f"  SKIP {source} (not found)")
                continue

            extracted = extract_word_region(audio, word_dur)

            # Normalize to -18 dBFS
            if extracted.dBFS > -80:
                extracted = extracted.apply_gain(-18.0 - extracted.dBFS)

            pools[word].append(extracted)

    for word, clips in pools.items():
        print(f"  {word}: {len(clips)} clips")

    if not all(pools.values()):
        print("Missing clips for one or more words. Cannot compose.")
        return

    # --- Compose on the grid ---
    total_beats = BARS * BEATS_PER_BAR
    total_ms = beat_to_ms(total_beats) + 3000  # 3s tail
    result = AudioSegment.silent(duration=total_ms, frame_rate=SAMPLE_RATE)

    # Beat assignments: tornado on 1, "full of" on 2, confetti on 3
    # Beat 4 is rest (or occasional ghost note)
    word_beat_map = {
        "tornado": 0,   # beat 1 of each bar
        "full of": 1,   # beat 2
        "confetti": 2,  # beat 3
    }

    placement_count = 0

    for bar in range(BARS):
        for word, beat_offset in word_beat_map.items():
            # Random omission: 20% chance of skipping
            if random.random() < 0.20:
                continue

            beat = bar * BEATS_PER_BAR + beat_offset
            position_ms = beat_to_ms(beat)

            # Timing jitter
            jitter = random.randint(-JITTER_MS, JITTER_MS)
            position_ms = max(0, position_ms + jitter)

            # Pick a random clip from the pool
            clip = random.choice(pools[word])

            # 25% chance of pitch shift (+/-1 or +/-2 semitones)
            if random.random() < 0.25:
                semitones = random.choice([-2, -1, 1, 2])
                clip = pitch_shift_audio(clip, semitones)

            # Slight gain variation for humanization
            gain_var = random.uniform(-2.0, 1.0)
            clip = clip.apply_gain(gain_var)

            if position_ms + len(clip) <= total_ms:
                result = result.overlay(clip, position=position_ms)
                placement_count += 1

        # Occasional ghost note on beat 4 (10% chance, random word)
        if random.random() < 0.10:
            beat = bar * BEATS_PER_BAR + 3
            position_ms = beat_to_ms(beat) + random.randint(-JITTER_MS, JITTER_MS)
            word = random.choice(list(pools.keys()))
            clip = random.choice(pools[word])
            clip = clip.apply_gain(-6.0)  # quieter ghost
            if position_ms + len(clip) <= total_ms:
                result = result.overlay(clip, position=max(0, position_ms))

    # Trim silence from the end
    target_duration = beat_to_ms(total_beats) + 1000  # 1s tail
    result = result[:target_duration]

    # Gentle fade out
    result = result.fade_out(1500)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result.export(OUTPUT_FILE, format="wav")
    print(f"\nPlaced {placement_count} words across {BARS} bars at {BPM} BPM")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Duration: {len(result) / 1000:.1f}s")


if __name__ == "__main__":
    main()
