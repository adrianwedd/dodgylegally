#!/usr/bin/env python3
"""Spectral Morph — sort assembled phrases by brightness and crossfade between them.

Takes the 16 assembled "tornado full of confetti" versions, orders them by
average spectral centroid (low to high), and plays them sequentially with
500ms crossfades. No delay, no pan — just the raw timbral shift from warm
closet to bright cathedral.

Output: tornado_compositions/spectral_morph.wav (~25s)
"""

from __future__ import annotations

import json
import os

import numpy as np
from pydub import AudioSegment


BASE = os.path.dirname(os.path.abspath(__file__))
ASSEMBLED_DIR = os.path.join(BASE, "tornado_assembled_supertight_v2")
MANIFEST = os.path.join(ASSEMBLED_DIR, "manifest.json")
OUTPUT_DIR = os.path.join(BASE, "tornado_compositions")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "spectral_morph.wav")

CROSSFADE_MS = 500


def avg_spectral_centroid(entry: dict) -> float:
    """Average spectral centroid across the three words in an assembled version."""
    centroids = [c["spectral_centroid"] for c in entry["clips"]]
    return sum(centroids) / len(centroids)


def main():
    with open(MANIFEST) as f:
        manifest = json.load(f)

    # Sort by average spectral centroid (warm -> bright)
    manifest.sort(key=avg_spectral_centroid)

    print("Spectral Morph — ordered by centroid (low -> high):")
    for entry in manifest:
        centroid = avg_spectral_centroid(entry)
        print(f"  {entry['filename']:25s}  centroid={centroid:.0f} Hz  score={entry['score']:.1f}")

    # Load and crossfade
    result = None
    for entry in manifest:
        path = os.path.join(ASSEMBLED_DIR, entry["filename"])
        if not os.path.exists(path):
            print(f"  SKIP {entry['filename']} (not found)")
            continue

        audio = AudioSegment.from_file(path, format="wav")

        # Normalize to -18 dBFS for consistent levels
        if audio.dBFS > -80:
            audio = audio.apply_gain(-18.0 - audio.dBFS)

        if result is None:
            result = audio
        else:
            # Crossfade: overlap the tail of the previous with the head of the next
            cf = min(CROSSFADE_MS, len(result) // 2, len(audio) // 2)
            result = result.append(audio, crossfade=cf)

    if result is None:
        print("No audio files found.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result.export(OUTPUT_FILE, format="wav")
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"Duration: {len(result) / 1000:.1f}s")


if __name__ == "__main__":
    main()
