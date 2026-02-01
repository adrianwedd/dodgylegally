# Case Study: The Sound of Confetti

**Goal:** Collect as many audio clips as possible related to "tornado full of confetti" from YouTube and compose them into a structured piece.

**Concept:** Break the phrase into its component words — "confetti", "tornado", "full of" — and search for each independently. What does a collage of those sounds become when arranged by energy?

---

## Step 1: Search Strategy

Searching YouTube for "tornado full of confetti" returns 20 results dominated by a confetti machine brand literally named "Tornado." YouTube matches video titles and descriptions, not concepts — so our poetic phrase collides with product marketing.

Searching "tornado confetti" (dropping "full of") returns largely the same videos: 12 of 20 results overlap. YouTube treats "full of" as filler.

The fix: stop searching for the phrase and start searching for its *ingredients*. We ran 7 separate queries, each targeting a different sonic angle:

| Query | Results | What it finds |
|-------|---------|---------------|
| `tornado full of confetti` | 20 | Confetti machines, live events |
| `confetti` | 30 | Songs named "Confetti" (Little Mix, Charlotte Cardin, Big K.R.I.T.) |
| `tornado` | 30 | Storm chaser footage, documentaries, dramatic weather |
| `full of` | 20 | Songs with "full of" in the title (Coldplay, Full of Hell) |
| `vintage confetti` | 15 | 1930s ambience, retro unboxings, lava lamps |
| `confetti hip hop beat` | 15 | Type beats, freestyle instrumentals |
| `confetti beat instrumental` | 10 | Karaoke tracks, instrumental remakes |

After deduplication: **137 unique videos**. The individual-word searches opened up entirely different sonic territory — storm audio, music tracks, hip-hop instrumentals — that the combined phrase never reached.

## Step 2: Download

Each video's midpoint was sampled — a 1-second clip extracted and converted to WAV.

**Initial batch (confetti-themed queries):** 30 of 45 downloads succeeded (67% hit rate). 15 failed due to ffmpeg conversion errors on incompatible source formats. Clip durations ranged from 1.0s to 9.5s.

**Expanded batch (all queries):** Attempted 137 unique videos across all search terms. After the initial 30 succeeded, YouTube began returning HTTP 403 errors, blocking further downloads. Final count: 32 unique clips.

| Metric | Value |
|--------|-------|
| Videos found | 137 |
| Successfully downloaded | 32 |
| ffmpeg conversion errors | ~15 |
| YouTube rate-limit blocks | ~90 |
| Clip duration range | 1.0s – 9.5s |
| Total raw audio | ~110s |

## Step 3: Process

All 32 clips were processed into two variants each:

- **32 one-shots** (2 seconds max, normalized, fade-out)
- **32 loops** (1 second, cross-faded for seamless repeat)

```bash
dodgylegally process -i case_study_tornado/raw
```

All clips exceeded the 500ms minimum. No processing failures.

## Step 4: Compose

Three composition approaches, each an iteration on the last.

### A. Sequential combine

```bash
dodgylegally combine
```

The built-in `combine` command repeats each loop 3-4 times and concatenates them in filesystem order. **92 seconds.** Every clip gets equal time. No transitions, no dynamics — a raw inventory of everything we collected.

### B. Flat cross-fade

Cross-fading improves on concatenation. All 30 one-shots were shuffled and stitched with 200ms overlaps. A bed of 10 loops (each repeated 6x, mixed at -8dB) runs underneath for continuity. **48 seconds.** The transitions are smoother, but the piece has no shape — it starts and ends at the same energy.

### C. Structured composition

The key insight: pydub's `dBFS` property (decibels relative to full scale) measures each clip's loudness. Sorting by loudness creates a natural grouping — quiet ambient textures separate from mid-energy sounds separate from loud percussive hits. Arranging those groups sequentially gives the piece an arc.

```
Intro (9.5s)  →  Build (13.2s)  →  Peak (7.3s)  →  Outro (6.8s)
```

The clips were split into thirds by loudness (dBFS range: -60.8 to -7.3):

```python
clips.sort(key=lambda c: c["dBFS"])
quiet = clips[:len(clips)//3]            # -60.8 to -28 dBFS
mid   = clips[len(clips)//3:2*len(clips)//3]  # -28 to -14 dBFS
loud  = clips[2*len(clips)//3:]          # -14 to -7.3 dBFS
```

Each section uses different crossfade lengths to control pacing:

| Section | Clips | Crossfade | Technique |
|---------|-------|-----------|-----------|
| Intro | 6 quiet | 500ms | Slow fade-in, -3dB overall |
| Build | 10 mid | 200ms | Tighter cuts, rising energy |
| Peak | 8+ loud | 100ms | Extra clips overlaid at -4dB for density |
| Outro | 4 quiet | 400ms | 2-second fade-out |

Sections are stitched with 200-300ms crossfades between them. The result is normalized to 0dBFS.

**36 seconds.** The piece opens with room tone and distant machine hum, accelerates through confetti rustling and mid-range pops, hits a dense wall of cannon blasts and crowd noise, then dissolves back into quiet.

## Results

```
case_study_tornado/
├── raw/        30 files (22 MB)   — initial confetti-themed downloads
├── raw_v2/     13 files (1.2 MB)  — expanded search (before rate limit)
├── oneshot/    30 files (9.6 MB)  — 2-second one-shots
├── loop/       30 files (4.8 MB)  — 1-second loops
├── combined/   1 file  (17 MB)    — 92s sequential combine
└── composed/
    ├── confetti_tornado_composition.wav (8.7 MB) — 48s flat cross-fade
    └── confetti_tornado_v2.wav         (6.7 MB) — 36s structured piece
```

## YouTube Rate Limiting

Bulk downloading hit a wall. Here's the timeline:

**Requests 1-45 (confetti-themed queries):** 30 succeeded, 15 failed with ffmpeg exit code 8. These ffmpeg failures weren't rate limiting — they were caused by yt-dlp's `download_ranges` feature trying to seek to a video's midpoint in formats that don't support byte-range requests. The downloads themselves worked; the 1-second extraction didn't.

**Requests 46-100 (expanded queries, no delay):** Rapid-fire requests over ~3 minutes. Only 2 new clips succeeded. YouTube began serving 0-byte files — the HTTP response was 200 OK, but the content was empty.

**Requests 101+ (with 3-7s delays):** Full HTTP 403 Forbidden on every request. The IP was blocked.

**Requests 101+ (with browser cookies):** Same 403. Passing Chrome cookies via `--cookies-from-browser` made no difference — the block is IP-level, not session-level. YouTube doesn't care who you are, only how fast you're going.

### What we learned

The rate limit has two distinct failure modes, and they require different fixes:

| Problem | Cause | Fix |
|---------|-------|-----|
| ffmpeg exit code 8 | `download_ranges` seeks into unsupported formats | Download full audio, trim locally with pydub |
| HTTP 403 / empty files | Too many requests from one IP | Slow down, batch, or wait |

The ffmpeg failures are the bigger practical issue. They accounted for 15 of our first 45 attempts (33% of failures) and are entirely avoidable. yt-dlp's range extraction asks ffmpeg to seek into a video stream, which fails on formats like DASH where segments aren't byte-addressable. Downloading the full audio and trimming with pydub would have converted those 15 failures into successes.

### Mitigation for future runs

**Before the block (prevention):**
- Download in batches of 10-15 with 2-3 minute breaks between batches.
- Use yt-dlp's `--sleep-interval 10 --max-sleep-interval 30` for automatic pacing.
- Skip `download_ranges` entirely — download full audio, trim to 1 second locally.

**After the block (recovery):**
- Wait 15-30 minutes with no requests, then resume slowly.
- Spread collection across multiple sessions over hours.

**Potential tool improvements:**
- A `--delay` flag on the `download` subcommand for paced bulk collection.
- A `--no-range` flag to download full audio and trim locally, avoiding the ffmpeg seeking failures that caused a third of our errors.

## Key Differences from Case Study 1

| | Random Phrases | Themed Collection |
|-|---------------|-------------------|
| **Search input** | Random word pairs ("spinelet digeny") | Intentional variations on a theme |
| **What you get** | Completely unpredictable | Sonically related material |
| **Hit rate** | ~14% (28 attempts, 4 clips) | ~67% before rate limit |
| **Composition** | 14s from 4 clips | 36s structured piece from 32 clips |
| **Character** | Chaotic, surprising | Cohesive, arc-shaped |

## Limitations

**YouTube searches metadata, not audio.** "Tornado full of confetti" finds videos with those words in titles and descriptions — confetti machine product pages, not recordings of actual confetti tornados. The workaround (splitting into individual words) helps, but the fundamental constraint remains: you can't search YouTube for a *sound*.

**Bulk collection requires patience.** Our session hit YouTube's rate limit at ~50 rapid requests. The tool's default behavior (one request per phrase, no delay) works fine for small runs but needs pacing for large collections. This is a solvable problem — see the mitigation section above.

**The composition has no rhythmic structure.** Sorting by loudness gives the piece an energy arc, but the clips aren't aligned to a beat grid. A confetti cannon hit lands whenever it happens to fall in the sequence, not on a downbeat. Tempo-synced composition would require beat detection (librosa), time-stretching, and quantization — a meaningful step up in complexity.

**The best source material was blocked.** The "confetti" query surfaced hip-hop type beats, Little Mix instrumentals, and Charlotte Cardin tracks — exactly the musical backbone a more polished composition needs. The rate limit prevented downloading any of them. A patient, multi-session collection run would fill this gap.

## Reproducing This

```bash
pip install .

# Download in small batches with delays
dodgylegally download \
  --phrase "confetti tornado" \
  --phrase "confetti blizzard" \
  --phrase "confetti explosion slow motion" \
  -o case_study_tornado

# Wait a few minutes, then continue
dodgylegally download \
  --phrase "confetti cannon party" \
  --phrase "confetti" \
  --phrase "tornado" \
  -o case_study_tornado

# Process and combine
dodgylegally -o case_study_tornado process
dodgylegally -o case_study_tornado combine
```

For the structured composition, the custom sorting-by-loudness script uses only pydub operations and can be adapted for any set of samples.
