import glob
import os
import random

from pydub import AudioSegment


def combine_loops(loop_dir: str, output_dir: str, repeats: tuple[int, int] = (3, 4)) -> str | None:
    """Combine all loops into a versioned file. Returns output path, or None if no loops."""
    wav_files = glob.glob(os.path.join(loop_dir, "*.wav"))
    if not wav_files:
        return None

    os.makedirs(output_dir, exist_ok=True)
    combined = AudioSegment.empty()

    for filepath in wav_files:
        sound = AudioSegment.from_file(filepath, format="wav")
        repeat_count = random.randint(repeats[0], repeats[1])
        combined += sound * repeat_count

    version = 1
    while True:
        output_path = os.path.join(output_dir, f"combined_loop_v{version}.wav")
        if not os.path.exists(output_path):
            break
        version += 1

    combined.export(output_path, format="wav")
    return output_path
