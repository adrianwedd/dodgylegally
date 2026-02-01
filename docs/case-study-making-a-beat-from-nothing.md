# Case Study: Making a Beat from Nothing

**Goal:** Use dodgylegally to build a short musical piece entirely from random YouTube audio, with no preconceived idea of what it will sound like.

**Tools:** dodgylegally CLI, ffmpeg, a terminal.

---

## Step 1: Generate Search Phrases

dodgylegally pairs random words from a 5,000-word dictionary. The results are phrases no human would ever search for.

```bash
dodgylegally search --count 8
```

```
spinelet digeny
merchet missal
liothrix sceat
streyne string
goracco elysia
outreach kelpware
underly kapeika
zagged undrossy
```

These are the search queries that will be sent to YouTube. YouTube's search algorithm does its best to find *something* — and that mismatch between intent and result is where the interesting sounds come from.

## Step 2: Download Audio

Each phrase is searched on YouTube. dodgylegally grabs a 1-second clip from the midpoint of the first result and converts it to WAV.

```bash
dodgylegally search --count 28 | dodgylegally download --phrases-file -
```

Of 28 attempts across two batches, 4 clips survived:

| Phrase | YouTube ID | Duration | Size |
|--------|-----------|----------|------|
| goshen duress | 3Fr0nq9JJbM | 5.97s | 1.1 MB |
| beeswax watcher | Q0TiN5pxPZ4 | 4.47s | 859 KB |
| slubbing themelet | 9x4CIvGPIo8 | 7.47s | 1.4 MB |
| befit zygote | 5h_uC96VQuY | 2.47s | 475 KB |

**Hit rate: ~14%.** Most failures were ffmpeg conversion errors on incompatible source formats. This attrition is normal and part of the process — you're casting a wide net into the unknown.

The clips are longer than the requested 1 second because yt-dlp's segment extraction often includes extra frames at the boundaries. That extra material gets trimmed in the next step.

## Step 3: Process into Samples

Each raw clip is processed into two variants:

- **One-shot:** Truncated to 2 seconds max, normalized, with a fade-out. Good for drum hits, stabs, textures.
- **Loop:** Cross-faded 1-second segment designed to repeat seamlessly. Good for pads, drones, rhythmic elements.

```bash
dodgylegally process
```

```
Processing: goshen duress-3Fr0nq9JJbM.wav
  oneshot: oneshot_goshen duress-3Fr0nq9JJbM.wav
  loop:    loop_goshen duress-3Fr0nq9JJbM.wav
Processing: beeswax watcher-Q0TiN5pxPZ4.wav
  oneshot: oneshot_beeswax watcher-Q0TiN5pxPZ4.wav
  loop:    loop_beeswax watcher-Q0TiN5pxPZ4.wav
Processing: slubbing themelet-9x4CIvGPIo8.wav
  oneshot: oneshot_slubbing themelet-9x4CIvGPIo8.wav
  loop:    loop_slubbing themelet-9x4CIvGPIo8.wav
Processing: befit zygote-5h_uC96VQuY.wav
  oneshot: oneshot_befit zygote-5h_uC96VQuY.wav
  loop:    loop_befit zygote-5h_uC96VQuY.wav
```

All 4 clips were long enough to process (minimum 500ms required). Result: 4 one-shots at 2s each, 4 loops at 1s each.

## Step 4: Combine into a Piece

The combine step takes all loops, repeats each one 3-4 times (randomized), and concatenates them into a single file.

```bash
dodgylegally combine
```

```
Combined loop: combined/combined_loop_v1.wav
```

**Output: a 14-second audio piece** built from 4 one-second loops, each repeated 3-4 times and stitched together sequentially.

## Results

```
case_study_output/
├── raw/       4 files  (original downloads)
├── oneshot/   4 files  (2-second one-shots)
├── loop/      4 files  (1-second loops)
└── combined/  1 file   (14-second combined piece)
```

The full pipeline — from random words to a playable audio file — took about 2 minutes. What's *in* that audio is entirely unpredictable: speech fragments, music snippets, ambient noise, sound effects. Every run produces something different.

## Doing It All in One Command

The same result in a single invocation:

```bash
dodgylegally run --count 20 -o ~/Music/random_samples
```

This runs search, download, process, and combine as a single pipeline. Use a high count (20+) to compensate for the download failure rate.

## Using a Themed Word List

For more directed results, supply a custom word list:

```bash
echo -e "rain\nthunder\nstorm\nlightning\ndrizzle\nhail\nmonsoon\ndownpour" > weather.txt
dodgylegally run --count 10 --wordlist weather.txt -o ~/Music/weather_samples
```

The search phrases will still be random pairs ("thunder drizzle", "hail monsoon"), but the source material will skew toward weather-related videos — nature documentaries, ASMR rain recordings, storm chaser footage.

## What You Can Do With the Output

The generated samples are standard WAV files that work in any DAW or audio tool:

- **Load one-shots into a sampler** (Ableton Simpler, Logic EXS24, any MPC) and play them chromatically
- **Drop loops onto a timeline** and layer them for texture
- **Feed the combined file into a granular synthesizer** for further mangling
- **Use as source material for convolution reverb** — a 1-second clip of an unknown room becomes an impulse response
- **Batch-generate sample packs** by running the tool repeatedly with different word lists

## Reproducibility

Every run produces different output because:
1. The word pairs are randomly selected
2. YouTube search results change over time
3. Loop repeat counts are randomized (3-4x)

Two people running the same command at the same time will get completely different audio. That's the point.
