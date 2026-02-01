"""Multi-track stem export — individual stems + manifest alongside full mix."""

from __future__ import annotations

import glob
import json
import os
import random

from pydub import AudioSegment


def export_stems(loop_dir: str, output_dir: str, repeats: tuple[int, int] = (3, 4),
                 strategy: str = "sequential") -> dict:
    """Export individual stems and a full mix from loop files.

    Returns a dict with 'tracks' (list of track info) and 'full_mix' (path).
    """
    wav_files = sorted(glob.glob(os.path.join(loop_dir, "*.wav")))

    os.makedirs(output_dir, exist_ok=True)

    if not wav_files:
        manifest = {"tracks": [], "full_mix": None}
        manifest_path = os.path.join(output_dir, "manifest.json")
        Path_obj = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        return manifest

    # Apply strategy for ordering
    from dodgylegally.strategies import get_strategy
    strat = get_strategy(strategy)
    wav_files = strat.arrange(wav_files)

    tracks = []
    combined = AudioSegment.empty()
    current_ms = 0

    for i, filepath in enumerate(wav_files):
        sound = AudioSegment.from_file(filepath, format="wav")
        repeat_count = random.randint(repeats[0], repeats[1])
        stem_audio = sound * repeat_count
        stem_duration = len(stem_audio)

        # Export individual stem
        stem_name = f"stem_{i + 1:03d}_{os.path.basename(filepath)}"
        stem_path = os.path.join(output_dir, stem_name)
        stem_audio.export(stem_path, format="wav")

        tracks.append({
            "index": i + 1,
            "source": os.path.basename(filepath),
            "stem_file": stem_name,
            "start_ms": current_ms,
            "duration_ms": stem_duration,
            "repeats": repeat_count,
        })

        combined += stem_audio
        current_ms += stem_duration

    # Export full mix
    mix_path = os.path.join(output_dir, "full_mix.wav")
    combined.export(mix_path, format="wav")

    # Write manifest
    manifest = {
        "tracks": tracks,
        "full_mix": mix_path,
        "total_duration_ms": len(combined),
        "track_count": len(tracks),
    }
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    return manifest
