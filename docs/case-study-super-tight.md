# Case Study: Super-Tight Word Isolation

*Assembling "tornado full of confetti" from the space between syllables.*

---

## 1. Goal

A one-second clip is generous. Spoken words live in 200--800 milliseconds; the remaining time belongs to the speaker's breath, the room, the neighbouring sentence. When you splice three one-second clips together, you hear three rooms collide. The goal of this session was to strip away everything that isn't the word itself -- to isolate spoken fragments so cleanly that the splice points disappear into the silence between syllables.

The target phrase: **"tornado full of confetti"** -- three words sourced from dozens of YouTube speakers, each occupying a different acoustic space, each carrying the ghost of a different sentence.

## 2. Implementation

The library's `trim_word_centered()` function already supported word-boundary trimming via faster-whisper timestamps. The key parameter is `clip_duration_s=0`, which collapses the clip to just the whisper-detected word boundaries plus a configurable `pad_ms` of ambient padding on each side.

The pipeline:

1. **Whisper transcription** -- faster-whisper with word-level timestamps locates the target word within the clip
2. **Boundary extraction** -- the clip is trimmed to `[word_start - pad_ms, word_end + pad_ms]`
3. **Zero-crossing snap** -- edges are nudged to the nearest zero crossing (within 64 samples) to prevent click artifacts
4. **Micro-fades** -- 3--6ms fade-in and fade-out to soften any remaining transients
5. **Re-verification** -- the trimmed clip is passed back through whisper to confirm the word survived trimming

The result: clips that are *exactly as long as the word*, plus a thin halo of room tone.

## 3. Sourcing

Starting from 114 previously verified 1-second clips across three words:

| Word | Source clips | Super-tight generated | Re-verification |
|------|-------------|----------------------|-----------------|
| tornado | 53 | 53 | 100% |
| confetti | 49 | 49 | 100% |
| full of | 12 | 12 | 100% |
| **Total** | **114** | **114** | **100%** |

Every clip that had been verified at the 1-second level survived re-trimming to word boundaries. Zero rejections. The whisper timestamps were precise enough that no spoken content was lost in the trim.

## 4. Pad Comparison

Three pad values were tested: 50ms, 80ms, and 120ms. The question was aesthetic rather than technical -- all three produced clean, verified clips. The difference was in how much *room* survived the trim.

### Duration distributions at 50ms pad

```
confetti (49 clips)   range: 417-908ms  avg: 609ms  median: 578ms
   400-499ms  #########              (9)
   500-599ms  ######################  (22)
   600-699ms  ##########              (10)
   700-799ms  ###                     (3)
   800-899ms  ####                    (4)
   900-999ms  #                       (1)

full of (12 clips)    range: 399-609ms  avg: 492ms  median: 499ms
   300-399ms  #                       (1)
   400-499ms  ######                  (6)
   500-599ms  ####                    (4)
   600-699ms  #                       (1)

tornado (53 clips)    range: 319-769ms  avg: 485ms  median: 459ms
   300-399ms  ##                      (2)
   400-499ms  #############################  (39)
   500-599ms  #######                 (7)
   600-699ms  ####                    (4)
   700-799ms  #                       (1)
```

### Cross-pad comparison

| | | min | avg | median | max |
|---|---|-----|-----|--------|-----|
| **confetti** | 50ms | 417 | 609 | 578 | 908 |
| | 80ms | 479 | 665 | 638 | 939 |
| | 120ms | 558 | 741 | 719 | 976 |
| **full of** | 50ms | 399 | 492 | 499 | 609 |
| | 80ms | 457 | 550 | 558 | 639 |
| | 120ms | 537 | 626 | 638 | 696 |
| **tornado** | 50ms | 319 | 485 | 459 | 769 |
| | 80ms | 379 | 546 | 520 | 797 |
| | 120ms | 458 | 622 | 599 | 839 |

**Finding:** 50ms clips sound clinical -- the word snaps into existence and vanishes. 120ms preserves enough room tone that the clip breathes. You can hear the space the speaker occupied: a closet, a studio, a kitchen. The 80ms pad sits between -- clean but not sterile. For assembly, all three pad variants were made available to the scorer, which could then choose whichever best matched its neighbours.

## 5. Assembly

The assembly pipeline from `tornado_assemble.py` scores every possible combination of (tornado clip, "full of" clip, confetti clip) and ranks them by a weighted compatibility score.

### Scorer

The scorer evaluates adjacent clip pairs on three axes:

```
score = noise_floor_diff x 80 + spectral_centroid_diff x 20 + level_diff x 5
```

- **Noise floor (weight 80)** -- the dominant artifact at splice points. When two clips have different background noise levels, the splice sounds like a gate opening and closing. This is the single most audible problem and the hardest to fix in post.
- **Spectral centroid (weight 20)** -- a proxy for brightness and timbre. Two clips from similar acoustic spaces will have similar centroids. A warm closet recording next to a bright studio recording creates perceptual whiplash.
- **Level (weight 5)** -- correctable via gain matching, but still a signal that the recordings differ fundamentally. Low weight because it's the easiest to fix.

### No-reuse constraint

The v2 assembly enforced a hard constraint: no source clip could appear in more than one assembled version. This forced the scorer deeper into the combinatorial space, producing 20 versions with genuinely different timbral characters rather than 20 minor variations of the same best clips.

### Assembly results

| Version | Score | Duration | Character |
|---------|-------|----------|-----------|
| v01 | 2.79 | 1559ms | Closest match -- similar room tone, similar brightness |
| v02 | 4.08 | 1858ms | Warm, close-mic'd speakers |
| v03 | 4.77 | 1417ms | Clean educational recordings |
| v04 | 5.04 | 1438ms | Quiet, controlled environments |
| v05 | 5.05 | 1258ms | Medium energy, consistent noise floor |
| v06 | 5.62 | 1457ms | Bright, high-centroid cluster |
| v07 | 5.66 | 1458ms | Dark, warm cluster |
| v08 | 5.96 | 1259ms | Balanced mid-range |
| v09 | 6.35 | 1278ms | Higher noise floor, energetic |
| v10 | 7.52 | 1280ms | Very quiet speakers |
| v11 | 7.75 | 1919ms | Mixed pad variants |
| v12 | 8.85 | 1458ms | All-tight (original 1s clips) |
| v13 | 9.38 | 1358ms | Mixed sources, quiet |
| v14 | 11.12 | 1157ms | Shortest version, dark timbre |
| v15 | 11.44 | 1858ms | Longest, includes a "long" pad clip |
| v16 | 13.97 | 1739ms | Low centroid outlier |
| v17 | 15.54 | 1337ms | Noise floor mismatch becoming audible |
| v18 | 16.47 | 1618ms | High centroid outlier (4000+ Hz) |
| v19 | 17.24 | 1278ms | Very quiet tornado, loud confetti |
| v20 | 19.35 | 1579ms | Most divergent -- different worlds |

Score range: **2.79 -- 19.35** (lower = smoother splice).
Duration range: **1157ms -- 1919ms**.

## 6. Widening the Pool

The bottleneck was "full of." A function word -- unstressed, brief, swallowed between content words. Speakers don't emphasise it. YouTube auto-captions frequently miss it. The initial pool contained just 12 verified clips, barely enough for the no-reuse constraint.

Twenty new search phrases were crafted to target contexts where "full of" would be spoken clearly:

- **Idiom explainers** -- "full of beans idiom meaning," "full of hot air meaning origin"
- **Read-alouds** -- "bucket full of dinosaurs read aloud," "sky full of stars narration"
- **Story narration** -- "the room was full of people story," "pockets full of rocks story explained"
- **Challenges** -- "mouth full of food challenge," "bag full of cash found"
- **Educational** -- "full of yourself meaning explained," "full of pronunciation English"

The strategy targeted contexts where the phrase would be spoken deliberately -- language lessons, idiom explanations, dramatic narration -- rather than the conversational mumble where "full of" usually lives.

**Result:** The verified pool grew from 12 to 25 clips. The new clips came from cleaner, more deliberate speech contexts, which also improved the average noise floor and spectral consistency of the "full of" pool.

### Final inventory for v2 assembly

| Word | Verified clips | super_tight (50ms) | super_tight_80ms | super_tight_120ms | tight (1s) |
|------|---------------|-------------------|-----------------|-------------------|-----------|
| tornado | 64 | 44 | 5 | 39 | 64 |
| full of | 25 | 21 | 1 | 18 | 24 |
| confetti | 68 | 44 | 6 | 38 | 68 |

## 7. Composition: Cascade Canon

The 20 assembled versions became source material for a composition. The first piece: a canon where 16 voices enter one by one, accelerating, panning outward, each carrying the phrase "tornado full of confetti" into an increasingly dense wash.

### Parameters

- **Voices:** 16 (top 80% by score, versions 1--16)
- **Entry interval:** Accelerando from 2200ms to 323ms (decay factor 0.88)
- **Delay:** 300ms initial, growing to 900ms per voice, 3 repeats, 0.35 feedback
- **Pan:** Alternating L/R, spreading from center to +/-0.8
- **Gain:** Ducking from 0.0dB to -4.0dB for later entries
- **Target loudness:** -16 dBFS
- **Duration:** 21.3 seconds (including 3s delay tail)

### Entry map

| Time | Version | Score | Delay | Pan | Gain |
|------|---------|-------|-------|-----|------|
| 0.0s | v01 | 2.8 | 300ms | C | 0.0dB |
| 2.2s | v02 | 4.1 | 340ms | L0.1 | -0.3dB |
| 4.1s | v03 | 4.8 | 380ms | R0.1 | -0.5dB |
| 5.8s | v04 | 5.0 | 420ms | L0.2 | -0.8dB |
| 7.3s | v05 | 5.1 | 459ms | R0.2 | -1.1dB |
| 8.7s | v06 | 5.6 | 499ms | L0.3 | -1.3dB |
| 9.8s | v07 | 5.7 | 540ms | R0.3 | -1.6dB |
| 10.8s | v08 | 6.0 | 580ms | L0.4 | -1.9dB |
| 11.7s | v09 | 6.3 | 619ms | R0.4 | -2.1dB |
| 12.5s | v10 | 7.5 | 660ms | L0.5 | -2.4dB |
| 13.2s | v11 | 7.8 | 699ms | R0.5 | -2.7dB |
| 13.8s | v12 | 8.9 | 740ms | L0.6 | -2.9dB |
| 14.4s | v13 | 9.4 | 780ms | R0.6 | -3.2dB |
| 14.8s | v14 | 11.1 | 820ms | L0.7 | -3.5dB |
| 15.3s | v15 | 11.4 | 860ms | R0.7 | -3.7dB |
| 15.6s | v16 | 14.0 | 900ms | L0.8 | -4.0dB |

The piece begins as a single clear voice saying "tornado full of confetti." By the midpoint, voices overlap and the phrase dissolves into rhythm. By the end, the words are gone entirely -- just the cadence of three stressed syllables repeating in a wash of delay feedback and room tone.

## 8. What We Learned

**Whisper boundaries are precise enough for clean word isolation.** The 100% re-verification rate across 114 clips means that faster-whisper's word-level timestamps reliably capture the onset and release of spoken words. The zero-crossing snap adds safety, but the timestamps alone are within a few tens of milliseconds of the perceptual boundary.

**`pad_ms` controls the aesthetic, not the quality.** All three pad levels (50ms, 80ms, 120ms) produced usable clips. The choice is artistic: 50ms for clinical precision, 120ms for ambient context, 80ms for a balanced default. Making all variants available to the scorer was the right call -- it let the algorithm match clips by room tone as well as by word.

**The scorer correctly identifies noise floor mismatch as the dominant splice artifact.** The 80x weight on noise floor difference reflects perceptual reality. When two clips have similar background noise levels, the splice is nearly invisible even if the spectral characteristics differ. When the noise floors diverge, no amount of crossfading hides the transition. The best-scoring assemblies (v01 at 2.79, v02 at 4.08) sound like a single speaker in a single room; the worst (v20 at 19.35) sounds like a collage -- which is also interesting, just differently.

**Function words are the bottleneck.** Content words like "tornado" and "confetti" are spoken with emphasis and appear in dedicated explainer videos. Function words like "full of" are swallowed, unstressed, and poorly captured by auto-captions. Targeted search phrases that force deliberate pronunciation (idiom explanations, language lessons) are the solution. The pool expansion from 12 to 25 clips was the difference between constrained and comfortable assembly.

**The no-reuse constraint reveals the character space.** By forcing each assembled version to use unique source clips, the 20 versions span a genuine range of timbral character -- from whisper-quiet ASMR recordings to energetic interviews. This turned out to be more valuable for composition than having 20 variations of the single best combination.

---

*Output: `tornado_assembled_supertight_v2/` -- 20 versions, manifest, and the beginning of a composition suite in `tornado_compositions/`.*
