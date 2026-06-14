---
name: video-srt
description: 'Language-agnostic video-to-SRT subtitle pipeline: ASR + LLM-driven language detection, singing removal, normalization, and translation'
version: 3.0.0
author: nkyang10
trigger: user asks to generate subtitles / transcribe video / 字幕 / 粵語字幕 / srt
source: https://github.com/nkyang10/video-srt
---

# video-srt

Multi-language subtitle generation using [yuesub-api](https://github.com/hon9kon9ize/yuesub-api) (SenseVoiceSmall ASR) + **LLM-driven** post-processing.

This skill is the canonical AI agent interface to the [video-srt](https://github.com/nkyang10/video-srt) project. It describes the complete pipeline from raw video to clean SRT, with exact prompts for each LLM stage.

## Prerequisites

- yt-dlp installed (`pip install yt-dlp`)
- ffmpeg installed
- yuesub-api at `~/tmp/yuesub-api/` (see Phase 1 setup)
- faster-whisper: `pip install faster-whisper` (music/singing fallback)
- LLM access: DeepSeek v4 flash recommended (no rate limits, handles full SRT in one pass)

### Initial yuesub-api setup (one-time)

```bash
cd ~/tmp
git clone https://github.com/hon9kon9ize/yuesub-api.git
cd yuesub-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Critical patch:** yuesub-api defaults to modelscope.cn (very slow outside China). Patch `transcriber/AutoTranscriber.py`:

```python
model="FunAudioLLM/SenseVoiceSmall"
hub="hf"
```

### VAD tuning

For quiet speech, lower threshold to 0.3 in `transcriber/AutoTranscriber.py`:

```python
vad_results = get_speech_timestamps(
    speech, self.vad_model,
    threshold=0.30,
    sampling_rate=16_000,
    min_speech_duration_ms=200,
    min_silence_duration_ms=50,
    speech_pad_ms=60,
    max_speech_duration_s=...,
)
```

## Pipeline

### Phase 1: Audio → Raw ASR

**Step 1.1 — Download audio:**

```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 -o "/tmp/yt_asr_%(id)s.%(ext)s" "<URL>"
```

**Step 1.2 — Convert to 16kHz mono WAV:**

```bash
ffmpeg -y -i /tmp/audio.mp3 -ar 16000 -ac 1 /tmp/audio.wav
```

**Step 1.3 — Run SenseVoiceSmall ASR:**

For videos **under 600s (10 min):**

```bash
cd ~/tmp/yuesub-api && source venv/bin/activate
python cli.py /tmp/audio.wav --output-dir /tmp/yuesub_output --max-length 8.0 --corrector opencc
```

For **longer videos**, segment first:

```bash
ffmpeg -y -i /tmp/audio.mp3 -f segment -segment_time 600 -c copy /tmp/asr_seg_%03d.mp3
mkdir -p /tmp/yuesub_chunks
for i in $(seq -w 0 10); do
  ffmpeg -y -i /tmp/asr_seg_${i}.mp3 -acodec pcm_s16le -ar 16000 -ac 1 /tmp/yuesub_chunks/chunk_${i}.wav
done
```

Then batch process:

```bash
YUESUB_PYTHON=~/tmp/yuesub-api/venv/bin/python3 \
  python3 ~/.hermes/skills/media/video-sub-general/scripts/process_chunks.py
```

Or via the video-srt package:

```bash
python3 -m video_srt.scripts.process_chunks.py
```

**Step 1.4 — Fallback: faster-whisper (music/singing)**

If `cli.py` returns "No transcriptions found" (common for concerts/live music), use faster-whisper:

```python
from faster_whisper import WhisperModel
model = WhisperModel('large-v3-turbo', device='cpu', compute_type='int8')
segments, info = model.transcribe(
    '/tmp/audio.wav',
    language='ja',  # or auto-detect
    beam_size=5,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500)
)
# Write SRT manually from segments generator
```

> **Key insight:** SenseVoiceSmall is ~30x realtime but fails on music. faster-whisper is ~0.5-1x realtime (CPU) but handles music well. A 145-min concert took ~3 min on 8-core CPU with faster-whisper.

### Phase 2: Language Detection

Pass the first 10-15 raw subtitle blocks to a subagent:

> Analyze these ASR subtitle blocks and determine:
> 1. Primary language (ISO 639-1 code: en/ja/zh/yue/ko/fr/de/es/pt/ru/auto)
> 2. Confidence (0-1)
> 3. Content type (talk/podcast/lecture/music/interview/tutorial/news)
> 4. Speaker style markers (colloquial patterns, filler words, sentence endings, keigo level)
> 5. Any garbled ASR artifacts detected (language mismatch, truncated words, model-name mangling)

The output drives ALL subsequent steps. Every normalization decision flows from this detection.

### Phase 3: Normalization + Singing Removal

Pass the **full SRT** to a single subagent with this prompt structure (populate `{}` from Phase 2 detection):

```
This is a [{language}] {content_type} video. The speaker uses {style_markers}.

=== ASR ARTIFACTS ===
{language artifacts detected in Phase 2 — garbled text patterns, known SenseVoiceSmall issues}

=== NORMALIZATION RULES ===
Apply these transformations appropriate for [{language}]:

**CRITICAL — Singing removal:** Classify EVERY block as SPEECH or SINGING.
Remove ALL SINGING blocks entirely — 所有歌唱/歌詞部分唔打字幕，淨係保留對話/MC/旁白部分。
If a block contains a mix of speech and singing, remove it.

General rules (all languages):
- Max 3 lines per block, max 25 chars (CJK) or 60 chars (Latin) per line
- Add punctuation mid-sentence (、， for CJK, commas for Latin)
- No period at end of subtitle line
- Split at natural phrase boundaries
- Keep proper nouns (brand names, model names, abbreviations) as-is
- Fix garbled ASR text: truncations, language-hallucinated characters, mangled model names
- Preserve speaker's stylistic markers unless distractingly colloquial

Language-specific rules:

English: gonna→going to, wanna→want to, gotta→have to, yeah→yes, ain't→is not,
remove fillers (um/uh/like/you know), expand contractions

Japanese: ちゃう→てしまう, とく→ておく, って言う→と言う, けど→が/けれども,
ね/よ/な→formal context; fix SenseVoiceSmall 漢字 artifacts
(see references/sensevoice-japanese-artifacts.md for pattern catalog)

Mandarin: 然后→此外/接着, 就是说→即/也就是, 那个/呃/嗯→remove filler, 对→是的

Cantonese: 嘅→的, 喺→在, 唔係→不是, 哋→們, 咗→了, 係→是, 噉/咁→這樣/那麼,
睇→看, 話→說, 話畀→告訴, 俾/畀→給, 冇→沒有, 嚟→來, 諗→想/思考, 識→懂/會,
佢→他/她, 呢個→這個, 嗰個→那個, 邊個→誰, 點解→為什麼, 乜嘢/咩→什麼
Output: Hong Kong Traditional Chinese (繁體), 25 CJK chars/line max
(see references/cantonese-conversion-table.md for full table)

Korean: remove fillers (음/어/근데), normalize 반말↔존댓말 based on context

European: expand contractions, unify dialect spellings, remove fillers

=== FULL SRT ===
[Full SRT content here]

Output the COMPLETE normalized SRT with all blocks. Preserve all timestamps
exactly. Renumber sequentially after removing singing blocks.
```

> **Note:** 150+ blocks in one subagent call works fine with DeepSeek v4 flash (confirmed: 158 blocks from an 11:38 video). No rate limit concerns.

### Phase 4: Gap Fix

```bash
python3 ~/.hermes/skills/media/video-sub-general/scripts/fix_subtitle_gaps.py normalized.srt --max-gap 2.0
```

Or via video-srt package:

```bash
video-srt fix-gaps normalized.srt --max-gap 2.0
```

This step is NOT redundant after VAD — a 158-block SRT had 132 gaps smoothed, tightening timing and removing empty blocks.

### Phase 5: Translation (Optional)

After singing is removed and speech is normalized, translate all remaining speech blocks to a target language via a single subagent call:

Rules:
- Preserve ALL timestamps, block numbers, SRT structure
- Keep proper nouns (model names, brands, abbreviations) as-is
- Apply target language subtitle conventions: max 25 CJK or 60 Latin chars per line, 3 lines max
- Add punctuation mid-sentence, no period at end
- Singing blocks were already removed — only process speech/MC content

Delivery: save as separate file (.srt), send via MEDIA tag, or email via mynote SMTP pattern.

## Quality Checks (Post-Merge)

After normalization + gap fix, verify:
- Any singing blocks leaked through?
- Any speech blocks incorrectly deleted?
- Remaining colloquial forms that should be normalized?
- Line length violations (>25 CJK or >60 Latin)?
- Valid timestamp sequence (no overlaps)?
- Sequential renumbering after singing removal?

## Reference Files

| File | Description |
|------|-------------|
| `references/cantonese-conversion-table.md` | Full 口語→語體文 mapping for Cantonese |
| `references/sensevoice-japanese-artifacts.md` | Japanese→Chinese hallucination patterns by category |
| `references/kalafina-concert-workflow.md` | End-to-end worked example (Japanese concert) |

## Known Issues

1. **SenseVoiceSmall language artifacts** — Most commonly Japanese→Cantonese/Chinese hallucination. LLM normalization can fix from context. See `references/sensevoice-japanese-artifacts.md`.

2. **SenseVoiceSmall VAD fails on music** — Concerts/live music produce zero segments. Switch to faster-whisper immediately; do NOT tune thresholds.

3. **SenseVoiceSmall `name` tag prefix** — `<|name|>` tag appears in output. Strip via LLM normalization rule.

4. **VAD misses ~30-40% quiet speech** — Lower threshold to 0.3 for soft-spoken content.

5. **Code-switching** — ASR accuracy varies by language pair when mixing languages.

## Limitations

- Very long videos (>60 min) need manual chunking for SenseVoiceSmall
- VAD inherently misses some quiet speech at any threshold
- LLM stages need a capable model (DeepSeek v4 flash recommended)

## For AI Agents Using This Skill

Key facts:
- **ASR backend:** SenseVoiceSmall (fast, speech) / faster-whisper (music fallback)
- **LLM model:** DeepSeek v4 flash — no rate limits, handles full SRT in one subagent call
- **Singing removal:** ALWAYS classify and remove; never subtitle songs
- **Language detection:** From first 10-15 blocks, drives all normalization
- **Normalization:** One subagent pass for full SRT (150+ blocks confirmed)
- **Translation:** Optional, applied after singing removal
- **Gap fix:** Always run even after VAD — catches significant gaps
- **Delivery:** SRT file via MEDIA tag or email attachment
