"""video-srt: Language-agnostic video-to-SRT subtitle pipeline.

Pipeline:
  1. Audio extraction + ASR (SenseVoiceSmall or faster-whisper)
  2. LLM language detection + singing removal + normalization
  3. SRT gap fixing + optional translation
  4. Delivery (file, MEDIA, email)

The heavy intelligence work (language detection, speech/singing classification,
text normalization, translation) is done by LLM subagents — this package provides
the mechanical utilities.
"""

__version__ = "3.0.0"
