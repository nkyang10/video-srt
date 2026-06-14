<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-blue.svg" alt="Version 3.0.0">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+">
</p>

# video-srt

**Language-agnostic video-to-SRT subtitle pipeline.** ASR + LLM-driven language detection, speech/singing classification, text normalization, and optional translation — all producing clean `.srt` subtitle files.

## Overview

video-srt converts any video (YouTube or local file) into properly formatted subtitles. It combines two technologies:

| Stage | Tool | What it does |
|-------|------|-------------|
| 1. Audio extraction | `yt-dlp` + `ffmpeg` | Download + convert to 16kHz mono WAV |
| 2. ASR | SenseVoiceSmall (fast) or faster-whisper (music) | Speech → raw text with timestamps |
| 3. Language detection | LLM subagent | Identifies language + content type + artifacts |
| 4. Normalization | LLM subagent | Fixes ASR errors, removes singing, normalizes per language |
| 5. Gap fixing | `fix_subtitle_gaps.py` | Smooths VAD gaps between blocks |
| 6. Translation (opt) | LLM subagent | Translate speech blocks to target language |

The mechanical parts (audio, ASR, SRT manipulation) are Python. The intelligence (language understanding, normalization, singing detection) is LLM-driven — making this adaptable to **any language** without per-language model training.

## Quick Start

### Installation

```bash
# 1. Install system deps
sudo apt install ffmpeg
pip install yt-dlp

# 2. Install video-srt
git clone https://github.com/nkyang10/video-srt.git
cd video-srt
pip install -e .

# 3. Install ASR backends
pip install faster-whisper  # fallback for music/singing

# 4. (Optional) Set up SenseVoiceSmall for faster ASR
git clone https://github.com/hon9kon9ize/yuesub-api.git ~/tmp/yuesub-api
cd ~/tmp/yuesub-api && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# ⚠️ Patch transcriber/AutoTranscriber.py: use model="FunAudioLLM/SenseVoiceSmall", hub="hf"
```

### CLI Usage

```bash
# Transcribe a YouTube video
video-srt transcribe "https://youtube.com/watch?v=..." --fix-gaps

# Transcribe a local file
video-srt transcribe /path/to/video.mp4 -l ja --fix-gaps

# Fix gaps in existing SRT
video-srt fix-gaps subtitles.srt --max-gap 2.0

# Validate SRT format
video-srt validate subtitles.srt

# Show SRT statistics + script distribution
video-srt info subtitles.srt
```

## Full Pipeline (AI Agent Flow)

The complete pipeline includes LLM-driven stages that require an AI agent (like Hermes or Claude) with access to a capable LLM (e.g., DeepSeek v4 flash).

### Phase 1: Audio → Raw SRT

```bash
# Download audio from YouTube
yt-dlp -x --audio-format mp3 -o "/tmp/audio.%(ext)s" "<URL>"

# Convert to 16kHz mono WAV
ffmpeg -y -i /tmp/audio.mp3 -ar 16000 -ac 1 /tmp/audio.wav

# Run ASR
cd ~/tmp/yuesub-api && source venv/bin/activate
python cli.py /tmp/audio.wav --output-dir /tmp/yuesub_output --max-length 8.0 --corrector opencc
```

For long videos (>10 min), segment first:

```bash
ffmpeg -y -i /tmp/audio.mp3 -f segment -segment_time 600 -c copy /tmp/asr_seg_%03d.mp3
# Convert each chunk → WAV → run cli.py on each
# Merge with: python3 video_srt/scripts/process_chunks.py
```

**Fallback for music/singing:** If SenseVoiceSmall returns "No transcriptions found", use faster-whisper:

```python
from faster_whisper import WhisperModel
model = WhisperModel('large-v3-turbo', device='cpu', compute_type='int8')
segments, info = model.transcribe('/tmp/audio.wav', language='ja',
    beam_size=5, vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500))
# Write segments to SRT
```

> **Decision rule:** Try SenseVoiceSmall first. If VAD returns zero segments, switch to faster-whisper immediately. Do not adjust VAD thresholds — music is a modality mismatch, not a tuning problem.

### Phase 2: Language Detection (LLM)

Pass the first 10-15 subtitle blocks to an LLM subagent:

> Analyze these ASR subtitle blocks and determine:
> 1. Primary language (ISO 639-1 code: en/ja/zh/yue/ko/fr/de/es/pt/ru/auto)
> 2. Confidence (0-1)
> 3. Content type (talk/podcast/lecture/music/interview/tutorial/news)
> 4. Speaker style markers (colloquial patterns, filler words, sentence endings, keigo level)
> 5. Any garbled ASR artifacts detected (language mismatch, truncated words, model-name mangling)

### Phase 3: Normalization + Singing Removal (LLM)

Pass the **full SRT** to a single LLM subagent. Construct the prompt from Phase 2's output:

```
This is a [{language}] {content_type} video. The speaker uses {style_markers}.

=== ASR ARTIFACTS ===
{garbled text patterns, known issues for this language}

=== NORMALIZATION RULES ===

**CRITICAL — Singing removal:** Classify EVERY block as SPEECH or SINGING.
Remove ALL SINGING blocks entirely. If a block contains a mix of speech and
singing, remove it.

General rules (all languages):
- Max 3 lines per block, max 25 chars (CJK) or 60 chars (Latin) per line
- Add punctuation mid-sentence (、， for CJK, commas for Latin)
- No period at end of subtitle line
- Split at natural phrase boundaries
- Keep proper nouns (brand names, model names, abbreviations) as-is
- Fix garbled ASR text: truncations, language-hallucinated characters
- Preserve speaker's stylistic markers unless distractingly colloquial

[Language-specific rules for {language}]

=== FULL SRT ===
[Full SRT content here]

Output the COMPLETE normalized SRT with all blocks. Preserve all timestamps
exactly. Renumber sequentially after removing singing blocks.
```

**Language-specific rules (examples):**

| Language | Rules |
|----------|-------|
| English | gonna→going to, wanna→want to, gotta→have to, yeah→yes, ain't→is not, remove fillers (um/uh/like/you know) |
| Japanese | ちゃう→てしまう, とく→ておく, って言う→と言う, けど→が/けれども, ね/よ/な→formal; fix 漢字 artifacts (see `references/sensevoice-japanese-artifacts.md`) |
| Mandarin | 然后→此外/接着, 就是说→即/也就是, 那个/呃/嗯→remove filler, 对→是的 |
| Cantonese | 嘅→的, 喺→在, 唔係→不是, 哋→們, 咗→了, 係→是, 睇→看, 話→說, 冇→沒有 (see `references/cantonese-conversion-table.md`) |
| Korean | remove fillers (음/어/근데), normalize 반말↔존댓말 |
| European | expand contractions, unify dialect spellings, remove fillers |

### Phase 4: Gap Fix

```bash
python3 -m video_srt.scripts.fix_subtitle_gaps.py normalized.srt --max-gap 2.0
```

This closes small VAD gaps by extending each block's end to 80ms before the next block's start. Also drops empty-text blocks and renumbers.

### Phase 5: Translation (Optional)

After singing is removed, optionally translate all remaining speech blocks:

> Preserve ALL timestamps and SRT structure. Keep proper nouns as-is.
> Apply target language conventions: max 25 CJK or 60 Latin chars per line, 3 lines max.
> Add punctuation mid-sentence, no period at end.

## Reference Documents

| Document | Description |
|----------|-------------|
| `references/cantonese-conversion-table.md` | Full 口語→語體文 (colloquial→formal Cantonese) mapping |
| `references/sensevoice-japanese-artifacts.md` | Catalog of SenseVoiceSmall Japanese→Chinese hallucination patterns |
| `references/kalafina-concert-workflow.md` | End-to-end worked example (Japanese concert, 2h25min) |

## VAD Tuning

| Content type | Threshold | Notes |
|-------------|-----------|-------|
| Lecture / speech | 0.5 | Clear, consistent volume |
| Interview | 0.3-0.4 | May have soft-spoken moments |
| Podcast | 0.35-0.45 | Varying speaker volume |
| Music-heavy | 0.3-0.35 | Quiet sections interspersed |
| Outdoor / noisy | 0.5-0.6 | Avoid noise false positives |
| Whispered | 0.2-0.25 | Aggressive capture needed |

## Known Issues

### SenseVoiceSmall language artifacts
Hallucinates characters from wrong languages — Japanese speech producing Cantonese/Chinese characters most commonly. See `references/sensevoice-japanese-artifacts.md` for patterns.

### SenseVoiceSmall VAD fails on music
Concerts and vocal music routinely produce zero segments. **Do not** tune thresholds — switch to faster-whisper immediately.

### SenseVoiceSmall `name` tag prefix
Output often includes `<|name|>` tag prefix artifacts. Strip these in LLM normalization.

## Limitations

- SenseVoiceSmall may produce artifacts in code-switching content
- VAD inherently misses ~30-40% quiet speech
- Very long videos (>60 min) need manual chunking for SenseVoiceSmall
- LLM stages require a capable model (DeepSeek v4 flash recommended)

## For AI Agents

This repository is designed to be consumed by AI agents. The `SKILL.md` file contains a Hermes-compatible skill definition that agents can load to understand the full pipeline, including the exact prompts needed for each LLM-driven stage.

Key facts for agents:
- **Primary ASR:** SenseVoiceSmall via yuesub-api (~30x realtime)
- **Fallback ASR:** faster-whisper large-v3-turbo (music/singing)
- **LLM:** DeepSeek v4 flash (no rate limits, handles full SRT in one pass)
- **Singing removal:** Classify every block, remove singing entirely
- **Language detection:** LLM-driven from first 10-15 blocks
- **Normalization:** Dynamic per detected language, one subagent pass

## License

MIT
