#!/usr/bin/env python3
"""Assemble "tornado full of confetti" from spoken-word clips.

Uses faster-whisper to verify each clip actually contains the target word,
extracts precise word boundaries, scores combinations for spectral and
level compatibility, then splices the best pairings with level-matched
audio, zero-crossing edges, and crossfades.

Usage:
    python tornado_assemble.py                # assemble with defaults
    python tornado_assemble.py --verify-only  # just scan and report
    python tornado_assemble.py --versions 10  # produce 10 versions
    python tornado_assemble.py --words "hello world"  # custom phrase
"""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import re
from dataclasses import asdict, dataclass

import numpy as np
from pydub import AudioSegment


# ------------------------------------------------------------------
# Clip verification and profiling
# ------------------------------------------------------------------
@dataclass
class VerifiedClip:
    """A clip where the target word has been confirmed via whisper."""

    path: str
    name: str
    target_word: str
    word_start_s: float
    word_end_s: float
    word_duration_ms: int
    clip_duration_ms: int
    rms_dbfs: float
    speech_rms: float  # linear RMS of the word region
    noise_rms: float  # linear RMS outside the word
    spectral_centroid: float


def _to_mono_float(audio: AudioSegment) -> tuple[np.ndarray, int]:
    """Convert AudioSegment to mono float64 array normalized to [-1,1]."""
    samples = np.array(audio.get_array_of_samples(), dtype=np.float64)
    sr = audio.frame_rate
    if audio.channels > 1:
        samples = samples.reshape(-1, audio.channels).mean(axis=1)
    samples /= 2 ** 15
    return samples, sr


def _rms(samples: np.ndarray) -> float:
    if len(samples) == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples ** 2)))


def _spectral_centroid(samples: np.ndarray, sr: int) -> float:
    if len(samples) < 256:
        return 0.0
    windowed = samples * np.hanning(len(samples))
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(windowed), 1.0 / sr)
    total = spectrum.sum()
    if total < 1e-10:
        return 0.0
    return float(np.sum(freqs * spectrum) / total)


def verify_clip(path: str, target_word: str, model) -> VerifiedClip | None:
    """Transcribe a clip and check if the target word is actually spoken.

    Uses word-level timestamps from faster-whisper. For multi-word targets,
    finds the full sequence within a 3s window.

    Returns a VerifiedClip with precise timing, or None if the word
    is not found.
    """
    audio = AudioSegment.from_file(path, format="wav")
    if audio.dBFS < -80:
        return None

    segments_iter, _info = model.transcribe(path, word_timestamps=True)
    all_words = []
    for seg in segments_iter:
        if seg.words:
            all_words.extend(seg.words)

    if not all_words:
        return None

    target_parts = target_word.strip().lower().split()
    patterns = [re.compile(r"\b" + re.escape(w) + r"\b", re.I) for w in target_parts]

    word_start = None
    word_end = None

    if len(target_parts) == 1:
        for w in all_words:
            if patterns[0].search(w.word):
                word_start = w.start
                word_end = w.end
                break
    else:
        for i, w in enumerate(all_words):
            if patterns[0].search(w.word):
                matched = [w]
                pi = 1
                for j in range(i + 1, min(i + 8, len(all_words))):
                    if pi < len(patterns) and patterns[pi].search(all_words[j].word):
                        matched.append(all_words[j])
                        pi += 1
                        if pi == len(patterns):
                            break
                if pi == len(patterns):
                    word_start = matched[0].start
                    word_end = matched[-1].end
                    break

    if word_start is None:
        return None

    # Measure audio properties around the verified word
    samples, sr = _to_mono_float(audio)
    start_samp = int(word_start * sr)
    end_samp = int(word_end * sr)
    end_samp = min(end_samp, len(samples))

    speech_samples = samples[start_samp:end_samp]
    noise_samples = np.concatenate([samples[:start_samp], samples[end_samp:]])

    return VerifiedClip(
        path=path,
        name=os.path.basename(path),
        target_word=target_word,
        word_start_s=word_start,
        word_end_s=word_end,
        word_duration_ms=int((word_end - word_start) * 1000),
        clip_duration_ms=len(audio),
        rms_dbfs=audio.dBFS,
        speech_rms=_rms(speech_samples),
        noise_rms=_rms(noise_samples),
        spectral_centroid=_spectral_centroid(speech_samples, sr),
    )


def verify_directory(directory: str, target_word: str, model,
                     pattern: str = "*.wav") -> tuple[list[VerifiedClip], list[str]]:
    """Scan all WAVs in a directory. Returns (verified, missed_names)."""
    wavs = sorted(glob.glob(os.path.join(directory, pattern)))
    verified = []
    missed = []
    for path in wavs:
        clip = verify_clip(path, target_word, model)
        if clip is not None:
            verified.append(clip)
        else:
            missed.append(os.path.basename(path))
    return verified, missed


# ------------------------------------------------------------------
# Scoring
# ------------------------------------------------------------------
def score_pair(a: VerifiedClip, b: VerifiedClip) -> float:
    """Score compatibility between two adjacent clips. Lower is better."""
    # Noise floor mismatch — most audible artifact at splice points
    noise_diff = abs(a.noise_rms - b.noise_rms)

    # Spectral centroid — brightness/timbre continuity
    mean_centroid = (a.spectral_centroid + b.spectral_centroid) / 2
    centroid_diff = abs(a.spectral_centroid - b.spectral_centroid) / max(mean_centroid, 1)

    # Level mismatch (correctable but still a signal of different recordings)
    mean_rms = (a.speech_rms + b.speech_rms) / 2
    level_diff = abs(a.speech_rms - b.speech_rms) / max(mean_rms, 1e-6)

    return noise_diff * 80 + centroid_diff * 20 + level_diff * 5


def score_sequence(clips: list[VerifiedClip]) -> float:
    """Score a full sequence by summing adjacent pair scores."""
    if len(clips) < 2:
        return 0.0
    total = 0.0
    for a, b in zip(clips, clips[1:]):
        total += score_pair(a, b)
    # Penalize very quiet clips
    total += sum(3.0 for c in clips if c.speech_rms < 0.01)
    return total


# ------------------------------------------------------------------
# Assembly
# ------------------------------------------------------------------
def _find_zero_crossing(samples: np.ndarray, target: int,
                        search_range: int = 64) -> int:
    lo = max(0, target - search_range)
    hi = min(len(samples) - 1, target + search_range)
    region = samples[lo:hi]
    if len(region) < 2:
        return target
    signs = np.sign(region)
    crossings = np.where(np.diff(signs) != 0)[0]
    if len(crossings) == 0:
        return target
    closest = crossings[np.argmin(np.abs(crossings + lo - target))]
    return int(closest + lo)


def extract_word(clip: VerifiedClip, pad_before_ms: int = 20,
                 pad_after_ms: int = 30) -> AudioSegment:
    """Extract just the verified word from a clip with tight padding.

    Trims to whisper-verified word boundaries, snaps to zero crossings,
    applies micro-fades.
    """
    audio = AudioSegment.from_file(clip.path, format="wav")
    start_ms = max(0, int(clip.word_start_s * 1000) - pad_before_ms)
    end_ms = min(len(audio), int(clip.word_end_s * 1000) + pad_after_ms)
    trimmed = audio[start_ms:end_ms]

    # Snap edges to zero crossings
    samples, sr = _to_mono_float(trimmed)
    if len(samples) > 128:
        new_start = _find_zero_crossing(samples, 0, search_range=64)
        new_end = _find_zero_crossing(samples, len(samples) - 1, search_range=64)
        new_end = max(new_end, new_start + 1)
        start_trim_ms = int(new_start / sr * 1000)
        end_trim_ms = int(new_end / sr * 1000)
        trimmed = trimmed[start_trim_ms:end_trim_ms]

    # Micro-fades
    fade_ms = min(6, max(1, len(trimmed) // 8))
    trimmed = trimmed.fade_in(fade_ms).fade_out(fade_ms)

    return trimmed


def assemble_phrase(clips: list[VerifiedClip],
                    target_dbfs: float = -18.0,
                    gap_ms: int = 70,
                    crossfade_ms: int = 20) -> AudioSegment:
    """Assemble a phrase from a sequence of verified word clips.

    Each word is extracted at its whisper-verified boundaries,
    level-matched, and spliced with natural inter-word gaps.
    """
    if not clips:
        return AudioSegment.silent(duration=100)

    words: list[AudioSegment] = []
    for clip in clips:
        word_audio = extract_word(clip)
        # Level-match
        if word_audio.dBFS > -80:
            word_audio = word_audio.apply_gain(target_dbfs - word_audio.dBFS)
        words.append(word_audio)

    # Natural speech timing: function words ("full of") get shorter gaps
    # before them; content words ("tornado", "confetti") get standard gaps
    result = words[0]
    for i, word in enumerate(words[1:], 1):
        # Shorter gap before function words, standard otherwise
        this_gap = int(gap_ms * 0.6) if clips[i].target_word in ("of", "the", "a", "full of") else gap_ms
        silence = AudioSegment.silent(duration=this_gap, frame_rate=result.frame_rate)

        if crossfade_ms > 0 and len(result) > crossfade_ms and len(word) > crossfade_ms:
            result = result.append(silence + word, crossfade=crossfade_ms)
        else:
            result = result + silence + word

    return result


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def _default_sources():
    """Return the default word→directory mapping for 'tornado full of confetti'."""
    base = os.path.dirname(os.path.abspath(__file__))
    return [
        ("tornado", [
            os.path.join(base, "tornado_spoken", "tornado", "tight"),
            os.path.join(base, "spoken_clips", "tornado", "tight"),
        ]),
        ("full of", [
            os.path.join(base, "tornado_spoken", "full of", "tight"),
            os.path.join(base, "tornado_spoken", "full of", "long"),
            os.path.join(base, "spoken_clips", "full of", "tight"),
        ]),
        ("confetti", [
            os.path.join(base, "confetti_spoken", "tight"),
            os.path.join(base, "confetti_whisper", "tight"),
            os.path.join(base, "spoken_clips", "confetti", "tight"),
        ]),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verify-only", action="store_true",
                        help="Scan and report clip inventory, don't assemble")
    parser.add_argument("--versions", type=int, default=20,
                        help="Number of assembled versions to produce (default: 20)")
    parser.add_argument("--output", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "tornado_assembled"),
        help="Output directory")
    parser.add_argument("--whisper-model", default="base",
                        help="Whisper model size (default: base)")
    parser.add_argument("--gap-ms", type=int, default=70,
                        help="Inter-word gap in ms (default: 70)")
    parser.add_argument("--crossfade-ms", type=int, default=20,
                        help="Crossfade duration in ms (default: 20)")
    parser.add_argument("--target-dbfs", type=float, default=-18.0,
                        help="Target loudness in dBFS (default: -18)")
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Error: faster-whisper is required. Install with: pip install faster-whisper")
        return

    print(f"Loading whisper model '{args.whisper_model}'...")
    model = WhisperModel(args.whisper_model, compute_type="int8")

    # Verify all clips
    sources = _default_sources()
    inventory: dict[str, list[VerifiedClip]] = {}
    all_missed: dict[str, list[str]] = {}

    for target_word, directories in sources:
        verified = []
        missed = []
        for directory in directories:
            if not os.path.isdir(directory):
                print(f"  SKIP {directory} (not found)")
                continue
            v, m = verify_directory(directory, target_word, model)
            verified.extend(v)
            missed.extend(m)
        inventory[target_word] = verified
        all_missed[target_word] = missed

    # Report
    print("\n=== Clip Inventory ===")
    for word in inventory:
        clips = inventory[word]
        misses = all_missed[word]
        print(f"\n  '{word}': {len(clips)} verified, {len(misses)} rejected")
        for c in clips:
            print(f"    [{c.word_start_s:.3f}-{c.word_end_s:.3f}] "
                  f"{c.word_duration_ms:3d}ms  {c.rms_dbfs:+.1f}dB  "
                  f"noise={c.noise_rms:.4f}  {c.name}")
        if misses:
            print(f"    rejected: {', '.join(m[:30] for m in misses[:5])}"
                  + (f" (+{len(misses)-5} more)" if len(misses) > 5 else ""))

    if args.verify_only:
        return

    # Check we have clips for every word
    missing_words = [w for w, clips in inventory.items() if not clips]
    if missing_words:
        print(f"\n*** Cannot assemble: no verified clips for: {', '.join(missing_words)}")
        print("    Re-run the download scripts to source these words, then try again.")
        return

    # Score and rank all combinations
    word_order = [w for w, _ in sources]
    clip_lists = [inventory[w] for w in word_order]

    print(f"\nScoring {' x '.join(str(len(cl)) for cl in clip_lists)} combinations...")
    combos: list[tuple[float, list[VerifiedClip]]] = []
    for combo in itertools.product(*clip_lists):
        s = score_sequence(list(combo))
        combos.append((s, list(combo)))

    combos.sort(key=lambda x: x[0])
    print(f"  {len(combos)} total")

    # Show rankings
    print("\n  Best 10:")
    for i, (score, clips) in enumerate(combos[:10]):
        names = " + ".join(c.name[:28] for c in clips)
        print(f"    {i+1:2}. {score:.2f}  {names}")

    # Assemble
    n = min(args.versions, len(combos))
    os.makedirs(args.output, exist_ok=True)
    print(f"\nAssembling {n} versions -> {args.output}/")

    manifest = []
    for i, (score, clips) in enumerate(combos[:n]):
        phrase = assemble_phrase(clips, target_dbfs=args.target_dbfs,
                                gap_ms=args.gap_ms, crossfade_ms=args.crossfade_ms)
        filename = f"v{i+1:02d}_score{score:.1f}.wav"
        out_path = os.path.join(args.output, filename)
        phrase.export(out_path, format="wav")

        entry = {
            "version": i + 1,
            "score": round(score, 2),
            "duration_ms": len(phrase),
            "filename": filename,
            "clips": [],
        }
        for c in clips:
            entry["clips"].append({
                "word": c.target_word,
                "source": c.name,
                "word_start_s": c.word_start_s,
                "word_end_s": c.word_end_s,
                "rms_dbfs": round(c.rms_dbfs, 1),
            })
        manifest.append(entry)

        print(f"  {filename}: {len(phrase)}ms  "
              f"{' + '.join(c.name[:25] for c in clips)}")

    manifest_path = os.path.join(args.output, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest: {manifest_path}")
    scores = [m["score"] for m in manifest]
    durations = [m["duration_ms"] for m in manifest]
    print(f"Score range: {min(scores):.2f} — {max(scores):.2f} (lower = smoother)")
    print(f"Duration range: {min(durations)}ms — {max(durations)}ms")


if __name__ == "__main__":
    main()
