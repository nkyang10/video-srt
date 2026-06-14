# Kalafina Anniversary LIVE 2026 — worked example

Japanese female vocal group concert at NHK Hall, 2h25min, Japanese singing + MC.
Generated Traditional Chinese SRT subtitles.

## Summary

| Step | Tool | Time | Output |
|------|------|------|--------|
| Audio extraction | ffmpeg | ~90s | 16kHz mono WAV, 2h25min |
| ASR | faster-whisper large-v3-turbo (CPU) | ~3min | 266 Japanese SRT blocks |
| Gap fix | fix_subtitle_gaps.py | <1s | 266 blocks, 2 gaps fixed |
| Translation | subagent (DeepSeek v4 flash) | ~80s | 266 Traditional Chinese blocks |

## Commands

### 1. Audio extraction
```bash
ffmpeg -y -i "Kalafina Anniversary LIVE 2026.mp4" -vn \
  -acodec pcm_s16le -ar 16000 -ac 1 full_audio.wav
```

### 2. faster-whisper transcription (background for long audio)
```python
from faster_whisper import WhisperModel
model = WhisperModel('large-v3-turbo', device='cpu', compute_type='int8')
segments, info = model.transcribe(
    'full_audio.wav',
    language='ja',
    beam_size=5,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500)
)
# Write SRT manually from segments generator
```

### 3. Gap fix
```bash
python3 fix_subtitle_gaps.py raw_japanese.srt --max-gap 2.0 --output fixed_japanese.srt
```

### 4. Translation via subagent
Single subagent call with the full 266-block SRT. Prompt rules:
- Preserve ALL timestamps, block numbers, SRT structure
- MC: conversational Traditional Chinese
- Song lyrics: poetic Chinese matching singing rhythm
- Proper names: Kalafina, Wakana/Keiko/Hikaru, NHK Hall, song titles kept as-is
- Max 25 CJK chars per line, 3 lines max
- Chinese punctuation naturally, no period at block end
- Section cues (3回L, 3回C, etc.): keep as-is

## 歌唱移除規則

所有歌唱/歌詞部分一律唔打字幕。只保留 MC/對話/旁白：

- **純歌唱 block** → 直接刪除
- **混合 block（唱緊一半講嘢）** → 成個 block 刪除，避免斷裂
- **MC / 成員介紹 / 觀眾互動** → 保留，正常翻譯
- **樂器獨奏 / 純音樂段落** → 刪除（無歌詞）

## Key learnings

1. **SenseVoiceSmall fails on music** — returned "No transcriptions found" for all 15 chunks of 600s audio. VAD cannot segment singing. Immediate fallback to faster-whisper required.
2. **faster-whisper large-v3-turbo on CPU** — 276% CPU on 8-core, 2.8GB RAM, completed 2h25min in ~3min. No chunking needed.
3. **Quality** — Japanese transcription was clean. No language hallucination artifacts. Song lyrics slightly imperfect but MC sections very accurate.
4. **266 blocks in one subagent** — DeepSeek v4 flash handled the full translation pass without issues. Input was ~18KB SRT text.
5. **Delivery** — SRT file delivered via MEDIA tag or email attachment
