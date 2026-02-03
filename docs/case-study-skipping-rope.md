# Case Study: Skipping Rope Chanting

*Capturing playground chanting, percussive rope sounds, and ambient atmosphere as separate sample layers from the same video sources.*

## Goal

Use playground skipping rope footage as raw material for music sampling. The challenge: these videos contain three distinct sound layers tangled together — rhythmic chanting, the percussive slap of rope and feet, and the diffuse wash of playground ambience. Rather than using stem separation (which struggles with non-musical content), extract all three layer types directly from the audio using analysis-driven windowing.

## Search Strategy

Three phrase categories, ~30 phrases each (~90 total):

| Category | Strategy | Example phrases |
|----------|----------|----------------|
| Chant | Named rhymes, compilations, PE footage, cultural variants | "cinderella dressed in yella skipping rope", "jump rope rhymes for kids" |
| Percussion | Close-mic/ASMR, fitness/no-music, slow-motion, feet/clapping | "jump rope sound effect", "boxer skipping rope training silent" |
| Atmosphere | Field recordings, outdoor textures, documentary | "playground ambience recording", "school recess sounds" |

**Key insight:** Percussion phrases targeting fitness videos (no background music) yield cleaner onset-only windows than children's footage where chanting and rope sounds overlap. Atmosphere phrases work best when targeting explicit "field recording" or "ambience" terms — generic playground searches return videos with too much discrete activity.

## Three-Mode Extraction

Every downloaded video gets all three extraction passes. One download, three clip types.

### Chant detection (whisper + word density)

1. Transcribe full audio with faster-whisper (word-level timestamps)
2. Search for anchor words: cinderella, teddy, bear, jump, skip, rope, one, two, three...
3. Sliding 3s window: measure word density and inter-word intervals
4. If median interval < 600ms and density >= 2 words/sec = rhythmic chanting
5. Expand region to full chanting section
6. Extract at three durations (2s / 4s / 8s) centered on region
7. Re-verify: trimmed clip must contain >= 3 whisper-detected words

### Percussion detection (onset density + speech absence)

1. Run librosa onset detection on full audio
2. Reuse whisper timestamps from chant step (no duplicate transcription)
3. Find 2s windows where: onsets present AND no whisper words (speech-free)
4. Rank by onset density; extract densest clusters
5. Quality gate: reject if spectral centroid > 3000Hz (residual speech)

### Atmosphere extraction (energy windowing)

1. Compute RMS in 500ms windows across full recording
2. Find longest contiguous region with < 6dB RMS variation (steady-state)
3. Extract at three durations (4s / 8s / 15s) from this region
4. Quality gates: reject if > -20 dBFS (discrete event) or < -50 dBFS (silence)

### Clip duration table

| Category | Short | Medium | Long |
|----------|-------|--------|------|
| Chant | 2.0s | 4.0s | 8.0s |
| Percussion | 0.5s | 1.0s | 2.0s |
| Atmosphere | 4.0s | 8.0s | 15.0s |

## Profiling Results

After sourcing, each clip is profiled with category-specific analysis:

- **Chant clips**: BPM (via beat tracking), word density (words/sec), spectral centroid, key
- **Percussion clips**: onset density (onsets/sec), peak transient level, spectral centroid
- **Atmosphere clips**: energy variance (dB standard deviation), RMS level, spectral centroid

**Expected distributions:**

Chant BPM clusters around 100-130 BPM (the natural pace of children's rhythmic speech). Percussion onset density varies widely: fitness rope videos produce steady 4-8 onsets/sec, while playground footage gives irregular 2-5 onsets/sec clusters. Atmosphere clips should show low energy variance (< 3dB) by construction — the extraction filter enforces this.

## Scoring and Assembly

### Within-category scoring

**Chant pairs** — weighted formula:
```
bpm_diff x 40 + key_diff x 30 + noise_diff x 20 + centroid_diff x 10
```
BPM matching dominates because temporal alignment matters most for chanting medleys.

**Percussion pairs** — weighted formula:
```
onset_density_diff x 50 + centroid_diff x 30 + level_diff x 20
```
Onset density match ensures rhythmic consistency in percussion loops.

### Cross-layer scoring

```
bpm_match x 60 + level_balance x 25 + spectral_separation x 15
```
Favors combinations where: chant and percussion share tempo, levels are properly staged (atmosphere quietest, chant loudest), and spectral content is spread across frequency ranges.

### Assembly modes

- **Chant medley**: scored clips crossfaded into continuous sequence
- **Percussion loop**: hits placed on a beat grid at detected BPM
- **Full mix**: three layers gain-staged (atmosphere -22dB, percussion -16dB, chant -12dB)

## Compositions

Four pieces showing the range from raw documentary to heavy processing:

### A. "Playground" — raw documentary (~30s)

Atmosphere builds in over 3 seconds. Chanting enters. Full playground mix develops. Uses build-and-drop template. Minimal processing — preserves the roughness and liveness of the source material.

### B. "Rope Machine" — processed/mechanical (~21s)

Chant fragments quantised to a 100 BPM grid. Beat 1: 2s chant clip. Beat 3: percussion hit. Atmosphere bed underneath. 30% of chant clips get stutter+bitcrush via EffectChain, turning organic playground chanting into mechanical stuttering. Analogous to compose_word_scatter.py's approach to tornado clips.

### C. "Ghost Playground" — processed/haunting (~25s)

Reversed chant clips lowpassed at 800Hz create a dense backwards wash. At the midpoint, clean percussion hits emerge one at a time — the ghost of the playground heard through the reversed haze. Analogous to compose_reverse_reveal.py.

### D. "Tempo Shift" — raw, time-manipulated (~30s)

Chant medley time-stretched through an arc: 80 BPM (slow, dreamlike) to 140 BPM (frantic, sped-up playground) and back to 80 BPM. Percussion stretched in parallel. Atmosphere unchanged as a steady bed — the constant against which the temporal warping is heard. Uses transform.py's time_stretch_file().

## What We Learned

- **Three-mode extraction works.** A single downloaded video can yield chant, percussion, and atmosphere clips without stem separation. The key is using different analysis dimensions: word density for chanting, onset density minus speech for percussion, energy stability for atmosphere.

- **Whisper reuse is efficient.** Running transcription once and sharing word timestamps between the chant detector and the percussion speech-absence filter avoids duplicate work. This matters at scale: whisper is the slowest step.

- **Fitness videos are percussion gold.** Searching for "boxer skipping rope training silent" or "crossfit double unders no music" yields clean percussive audio with minimal speech contamination. Children's playground footage is better for chanting and atmosphere.

- **The steady-state filter is conservative.** Requiring < 6dB RMS variation and rejecting > -20 dBFS means atmosphere clips are genuinely ambient — no discrete shouts, whistles, or bells. The trade-off: shorter usable regions from each video.

- **Cross-layer scoring matters more than within-layer.** The best-sounding mixes come from combinations where spectral content is well-separated across layers, not from individually "best" clips. A bright chant + dark percussion + mid-frequency atmosphere beats three clips that all cluster around the same spectral centroid.

---

Output: `skipping_rope_clips/`, `skipping_assembled/`, `skipping_compositions/`
