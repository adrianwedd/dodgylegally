"""Confetti Composition Suite — 4 compositions from whisper and sample clips.

Produces:
  confetti_compositions/cascade/  — pitched whisper hits through a scale
  confetti_compositions/wash/     — ambient texture bed
  confetti_compositions/machine/  — glitch rhythm piece
  confetti_compositions/reveal/   — narrative arc with spoken word emergence
"""

from __future__ import annotations

import glob
import json
import os
import random
import shutil
import tempfile

from pydub import AudioSegment, effects as pydub_effects

from dodgylegally.effects import get_effect
from dodgylegally.effects.base import EffectChain
from dodgylegally.process import make_loop
from dodgylegally.stems import export_stems
from dodgylegally.strategies import get_strategy
from dodgylegally.strategies.templates import apply_template, load_template
from dodgylegally.transform import pitch_shift_file

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
WHISPER_TIGHT = os.path.join(BASE, "confetti_whisper", "tight")
WHISPER_LONG = os.path.join(BASE, "confetti_whisper", "long")
OUTPUT_ROOT = os.path.join(BASE, "confetti_compositions")


def _wavs(directory: str, pattern: str = "*.wav") -> list[str]:
    """Return sorted WAV paths from a directory."""
    return sorted(glob.glob(os.path.join(directory, pattern)))


def _whisper_clips(directory: str) -> list[str]:
    """Return WAV files with '_whisper_' in the name (spoken-word-centered)."""
    return sorted(f for f in _wavs(directory) if "_whisper_" in os.path.basename(f))


def _midpoint_clips(directory: str) -> list[str]:
    """Return WAV files with '_mid_' in the name (textural ambient)."""
    return sorted(f for f in _wavs(directory) if "_mid_" in os.path.basename(f))


def _stage(files: list[str], dest: str) -> list[str]:
    """Copy files into dest directory, return new paths."""
    os.makedirs(dest, exist_ok=True)
    staged = []
    for f in files:
        dst = os.path.join(dest, os.path.basename(f))
        shutil.copy2(f, dst)
        staged.append(dst)
    return staged


def _apply_effect_to_file(wav_path: str, chain: EffectChain, out_path: str) -> str:
    """Load a WAV, apply an effect chain, export to out_path."""
    audio = AudioSegment.from_file(wav_path, format="wav")
    processed = chain.apply(audio)
    processed.export(out_path, format="wav")
    return out_path


def _make_loops(wav_files: list[str], loop_dir: str) -> list[str]:
    """Run make_loop on each file into loop_dir, return loop paths."""
    os.makedirs(loop_dir, exist_ok=True)
    loops = []
    for f in wav_files:
        out = os.path.join(loop_dir, f"loop_{os.path.basename(f)}")
        make_loop(f, out)
        loops.append(out)
    return loops


def _write_fake_analysis(wav_path: str, bpm: float = 120.0,
                         key: str = "C major", lufs: float = -14.0):
    """Write a minimal analysis sidecar so strategies can read it."""
    audio = AudioSegment.from_file(wav_path, format="wav")
    sidecar = os.path.splitext(wav_path)[0] + ".json"
    data = {
        "analysis": {
            "bpm": bpm,
            "key": key,
            "loudness_lufs": lufs,
            "duration_ms": len(audio),
        }
    }
    with open(sidecar, "w") as f:
        json.dump(data, f, indent=2)


def _build_section(files: list[str], strategy_name: str, duration_s: float,
                   repeats: tuple[int, int] = (3, 4), **kwargs) -> AudioSegment:
    """Build one section: apply strategy ordering, concatenate with repeats, trim."""
    if not files:
        return AudioSegment.silent(duration=int(duration_s * 1000))

    strategy = get_strategy(strategy_name)
    ordered = strategy.arrange(files, **kwargs)
    target_ms = int(duration_s * 1000)

    section = AudioSegment.empty()
    for fp in ordered:
        if len(section) >= target_ms:
            break
        sound = AudioSegment.from_file(fp, format="wav")
        repeat_count = random.randint(repeats[0], repeats[1])
        section += sound * repeat_count

    if len(section) > target_ms:
        section = section[:target_ms]
    return section


def _export_composition(name: str, full_mix: AudioSegment,
                        loop_dir: str, strategy: str = "sequential"):
    """Export full_mix.wav and stems to confetti_compositions/{name}/."""
    comp_dir = os.path.join(OUTPUT_ROOT, name)
    os.makedirs(comp_dir, exist_ok=True)

    mix_path = os.path.join(comp_dir, "full_mix.wav")
    full_mix.export(mix_path, format="wav")
    print(f"  full_mix.wav: {len(full_mix) / 1000:.1f}s")

    stems_dir = os.path.join(comp_dir, "stems")
    manifest = export_stems(loop_dir, stems_dir, repeats=(2, 3), strategy=strategy)
    print(f"  stems: {manifest['track_count']} tracks")

    return mix_path


# ==================================================================
# Composition 1: Cascade — pitched whisper hits through a scale
# ==================================================================
def compose_cascade():
    print("\n--- Cascade ---")
    whispers = _whisper_clips(WHISPER_TIGHT) + _whisper_clips(WHISPER_LONG)
    print(f"  source: {len(whispers)} whisper clips")

    with tempfile.TemporaryDirectory() as tmp:
        pitched_dir = os.path.join(tmp, "pitched")
        os.makedirs(pitched_dir)

        # Pitch-shift each clip to a different semitone (-5 to +6)
        semitones = list(range(-5, 7))  # 12 values
        for i, src in enumerate(whispers[:12]):
            semi = semitones[i % len(semitones)]
            out = os.path.join(pitched_dir, f"pitch{semi:+d}_{os.path.basename(src)}")
            pitch_shift_file(src, out, semitones=semi)
            print(f"  pitch {semi:+d}: {os.path.basename(src)}")

        # Process into loops
        loop_dir = os.path.join(tmp, "loops")
        loops = _make_loops(_wavs(pitched_dir), loop_dir)

        # Write analysis sidecars (ascending loudness for build-and-drop)
        for i, lp in enumerate(loops):
            lufs = -24.0 + (i * 1.5)  # ascending
            _write_fake_analysis(lp, lufs=lufs)

        # Apply build-and-drop template
        template = load_template("build-and-drop")
        mix_path = os.path.join(tmp, "mix.wav")
        apply_template(template, loop_dir, mix_path, repeats=(2, 3))
        full_mix = AudioSegment.from_file(mix_path, format="wav")

        _export_composition("cascade", full_mix, loop_dir, strategy="loudness")


# ==================================================================
# Composition 2: Wash — ambient texture bed
# ==================================================================
def compose_wash():
    print("\n--- Wash ---")
    midpoints = _midpoint_clips(WHISPER_LONG)
    selected = midpoints[:20]
    print(f"  source: {len(selected)} long midpoint clips")

    with tempfile.TemporaryDirectory() as tmp:
        effected_dir = os.path.join(tmp, "effected")
        os.makedirs(effected_dir)

        lowpass_chain = EffectChain(effects=[(get_effect("lowpass"), {"freq": 800})])
        reverse_chain = EffectChain(effects=[(get_effect("reverse"), {})])

        for i, src in enumerate(selected):
            out = os.path.join(effected_dir, os.path.basename(src))
            if i < len(selected) // 2:
                _apply_effect_to_file(src, lowpass_chain, out)
            else:
                _apply_effect_to_file(src, reverse_chain, out)

        # Process into loops
        loop_dir = os.path.join(tmp, "loops")
        loops = _make_loops(_wavs(effected_dir), loop_dir)

        # Write analysis sidecars with varied keys for key_compatible ordering
        keys = ["C major", "G major", "D major", "A major", "E major",
                "F major", "Bb major", "Eb major", "Ab major", "Db major"]
        for i, lp in enumerate(loops):
            _write_fake_analysis(lp, key=keys[i % len(keys)], lufs=-18.0 + random.uniform(-3, 3))

        # Apply ambient-drift template
        template = load_template("ambient-drift")
        mix_path = os.path.join(tmp, "mix.wav")
        apply_template(template, loop_dir, mix_path, repeats=(3, 5))
        full_mix = AudioSegment.from_file(mix_path, format="wav")

        _export_composition("wash", full_mix, loop_dir, strategy="key_compatible")


# ==================================================================
# Composition 3: Machine — glitch rhythm piece
# ==================================================================
def compose_machine():
    print("\n--- Machine ---")
    midpoints = _midpoint_clips(WHISPER_TIGHT)
    selected = midpoints[:16]
    print(f"  source: {len(selected)} tight midpoint clips")

    with tempfile.TemporaryDirectory() as tmp:
        effected_dir = os.path.join(tmp, "effected")
        os.makedirs(effected_dir)

        stutter_bitcrush = EffectChain(effects=[
            (get_effect("stutter"), {"slice_ms": 60, "repeats": 3}),
            (get_effect("bitcrush"), {"bits": 6}),
        ])

        for src in selected:
            out = os.path.join(effected_dir, os.path.basename(src))
            _apply_effect_to_file(src, stutter_bitcrush, out)

        # Process into loops
        loop_dir = os.path.join(tmp, "loops")
        loops = _make_loops(_wavs(effected_dir), loop_dir)

        # Write analysis sidecars with varied tempos
        for i, lp in enumerate(loops):
            bpm = 80.0 + (i * 10)  # ascending tempo
            _write_fake_analysis(lp, bpm=bpm, lufs=-12.0)

        # Apply rhythmic-collage template
        template = load_template("rhythmic-collage")
        mix_path = os.path.join(tmp, "mix.wav")
        apply_template(template, loop_dir, mix_path, repeats=(2, 4))
        full_mix = AudioSegment.from_file(mix_path, format="wav")

        _export_composition("machine", full_mix, loop_dir, strategy="tempo")


# ==================================================================
# Composition 4: Reveal — narrative arc with spoken word emergence
# ==================================================================
def compose_reveal():
    print("\n--- Reveal ---")
    texture_clips = _midpoint_clips(WHISPER_LONG)[:8]
    whisper_clips = _whisper_clips(WHISPER_LONG)[:2] + _whisper_clips(WHISPER_TIGHT)[:2]
    print(f"  source: {len(texture_clips)} texture + {len(whisper_clips)} whisper clips")

    with tempfile.TemporaryDirectory() as tmp:
        # --- Texture section: lowpassed ambient ---
        texture_dir = os.path.join(tmp, "texture")
        os.makedirs(texture_dir)
        lowpass_chain = EffectChain(effects=[(get_effect("lowpass"), {"freq": 600})])
        for src in texture_clips:
            out = os.path.join(texture_dir, os.path.basename(src))
            _apply_effect_to_file(src, lowpass_chain, out)

        # --- Reveal section: clean whisper hits ---
        reveal_dir = os.path.join(tmp, "reveal")
        _stage(whisper_clips, reveal_dir)

        # --- Echo section: reversed whisper clips ---
        echo_dir = os.path.join(tmp, "echo")
        os.makedirs(echo_dir)
        reverse_chain = EffectChain(effects=[(get_effect("reverse"), {})])
        for src in whisper_clips:
            out = os.path.join(echo_dir, f"rev_{os.path.basename(src)}")
            _apply_effect_to_file(src, reverse_chain, out)

        # Process all groups into loops
        texture_loops_dir = os.path.join(tmp, "loops_texture")
        reveal_loops_dir = os.path.join(tmp, "loops_reveal")
        echo_loops_dir = os.path.join(tmp, "loops_echo")

        texture_loops = _make_loops(_wavs(texture_dir), texture_loops_dir)
        reveal_loops = _make_loops(_wavs(reveal_dir), reveal_loops_dir)
        echo_loops = _make_loops(_wavs(echo_dir), echo_loops_dir)

        # Write analysis sidecars
        for i, lp in enumerate(texture_loops):
            _write_fake_analysis(lp, lufs=-24.0 + i * 1.5)  # quiet ascending
        for lp in reveal_loops:
            _write_fake_analysis(lp, lufs=-8.0)  # loud (the reveal)
        for i, lp in enumerate(echo_loops):
            _write_fake_analysis(lp, lufs=-10.0 - i * 3)  # descending

        # Build sections manually (spoken-word-reveal template logic)
        # texture (6s) — filtered ambient, ascending loudness
        section_texture = _build_section(texture_loops[:4], "loudness", 6.0,
                                         repeats=(3, 4), descending=False)
        # emerge (5s) — remaining texture, still ascending
        section_emerge = _build_section(texture_loops[4:], "loudness", 5.0,
                                        repeats=(3, 4), descending=False)
        # reveal (4s) — clean whisper hits, sequential
        section_reveal = _build_section(reveal_loops, "sequential", 4.0,
                                        repeats=(2, 3))
        # echo (5s) — reversed whispers, descending loudness
        section_echo = _build_section(echo_loops, "loudness", 5.0,
                                      repeats=(3, 4), descending=True)

        full_mix = section_texture + section_emerge + section_reveal + section_echo

        # Also create a combined loop dir for stems export
        all_loops_dir = os.path.join(tmp, "loops_all")
        os.makedirs(all_loops_dir)
        for d in [texture_loops_dir, reveal_loops_dir, echo_loops_dir]:
            for f in _wavs(d):
                shutil.copy2(f, os.path.join(all_loops_dir, os.path.basename(f)))
                # Copy sidecars too
                sidecar = os.path.splitext(f)[0] + ".json"
                if os.path.exists(sidecar):
                    shutil.copy2(sidecar, os.path.join(
                        all_loops_dir, os.path.splitext(os.path.basename(f))[0] + ".json"))

        _export_composition("reveal", full_mix, all_loops_dir, strategy="loudness")


# ==================================================================
# Main
# ==================================================================
def main():
    random.seed(42)  # reproducible compositions
    print(f"Output: {OUTPUT_ROOT}")

    compose_cascade()
    compose_wash()
    compose_machine()
    compose_reveal()

    print("\n--- Done ---")
    for name in ["cascade", "wash", "machine", "reveal"]:
        mix = os.path.join(OUTPUT_ROOT, name, "full_mix.wav")
        if os.path.exists(mix):
            audio = AudioSegment.from_file(mix, format="wav")
            print(f"  {name}: {len(audio) / 1000:.1f}s")


if __name__ == "__main__":
    main()
