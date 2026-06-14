#!/usr/bin/env python3
"""video-srt CLI: Video-to-SRT subtitle pipeline entry point.

Usage:
  video-srt transcribe <url-or-file>         # Step 1: ASR only
  video-srt fix-gaps <srt> [--max-gap 2.0]  # Step 2: fix subtitle gaps
  video-srt validate <srt>                   # Validate SRT format
  video-srt info <srt>                       # Show SRT statistics

For the full LLM pipeline (language detection → normalization → singing removal
→ optional translation), see the SKILL.md or README.md — the AI-driven stages
must be run via an LLM agent with the provided prompts.
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .audio import download_audio, convert_to_wav, get_duration_ms
from .asr import transcribe
from .srt_utils import fix_gaps, validate_srt, count_blocks, parse_srt


def cmd_transcribe(args):
    """Transcribe audio/video to SRT."""
    source = args.source

    # Check if it's a URL or local file
    if source.startswith(("http://", "https://", "www.")):
        print(f"Downloading audio from: {source}")
        mp3 = download_audio(source)
        print(f"Audio saved: {mp3}")
    else:
        mp3 = Path(source)
        if not mp3.exists():
            print(f"Error: file not found: {source}", file=sys.stderr)
            return 1

    # Convert to WAV if needed
    wav_path = convert_to_wav(mp3)
    duration_ms = get_duration_ms(wav_path)
    print(f"Audio: {wav_path} ({duration_ms // 60000}m{(duration_ms % 60000) // 1000}s)")

    # Transcribe
    srt_path = transcribe(
        wav_path,
        language=args.language,
    )
    print(f"\nSRT output: {srt_path}")
    print(f"Blocks: {count_blocks(srt_path)}")

    if args.fix_gaps:
        result = fix_gaps(srt_path, max_gap_s=args.max_gap)
        print(f"Gaps fixed: {result['fixed']} / {result['blocks']} blocks")

    return 0


def cmd_fix_gaps(args):
    """Fix gaps in an SRT file."""
    result = fix_gaps(args.srt, max_gap_s=args.max_gap, output_path=args.output)
    print(f"Fixed {result['fixed']} gaps in {result['blocks']} blocks")
    if args.output:
        print(f"Output: {args.output}")
    return 0


def cmd_validate(args):
    """Validate SRT format."""
    issues = validate_srt(args.srt)
    if not issues:
        print(f"✅ {args.srt}: valid ({count_blocks(args.srt)} blocks)")
        return 0
    print(f"⚠️  {args.srt}: {len(issues)} issues:")
    for issue in issues:
        print(f"  • {issue}")
    return 1


def cmd_info(args):
    """Show SRT statistics."""
    blocks = parse_srt(args.srt)
    if not blocks:
        print(f"{args.srt}: empty or invalid")
        return 1

    total_duration_ms = blocks[-1]["t2"] - blocks[0]["t1"]
    text_blocks = [b for b in blocks if any(l.strip() for l in b["text"])]

    print(f"File:     {args.srt}")
    print(f"Blocks:   {len(blocks)}")
    print(f"Non-empty:{len(text_blocks)}")
    print(f"Duration: {total_duration_ms // 60000}m{(total_duration_ms % 60000) // 1000}s")
    print(f"Avg len:  {sum(len(' '.join(b['text'])) for b in text_blocks) // max(len(text_blocks), 1)} chars/block")

    # Detect language hint from character analysis
    cjk = sum(1 for b in text_blocks
              for line in b["text"]
              for c in line if '\u4e00' <= c <= '\u9fff')
    latin = sum(1 for b in text_blocks
                for line in b["text"]
                for c in line if c.isascii() and c.isalpha())
    hiragana = sum(1 for b in text_blocks
                   for line in b["text"]
                   for c in line if '\u3040' <= c <= '\u309f')
    katakana = sum(1 for b in text_blocks
                   for line in b["text"]
                   for c in line if '\u30a0' <= c <= '\u30ff')
    hangul = sum(1 for b in text_blocks
                 for line in b["text"]
                 for c in line if '\uac00' <= c <= '\ud7af')

    print(f"\nScript distribution:")
    total = cjk + latin + hiragana + katakana + hangul or 1
    print(f"  CJK:     {cjk:>6} ({100 * cjk // total:>2}%)")
    print(f"  Latin:   {latin:>6} ({100 * latin // total:>2}%)")
    print(f"  Hiragana:{hiragana:>6} ({100 * hiragana // total:>2}%)")
    print(f"  Katakana:{katakana:>6} ({100 * katakana // total:>2}%)")
    print(f"  Hangul:  {hangul:>6} ({100 * hangul // total:>2}%)")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="video-srt: Language-agnostic video-to-SRT subtitle pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--version", action="version", version=f"video-srt {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # transcribe
    p = subparsers.add_parser("transcribe", help="Transcribe audio/video to SRT")
    p.add_argument("source", help="YouTube URL or local audio/video file path")
    p.add_argument("--language", "-l", help="Language hint for ASR (e.g. 'ja', 'zh')")
    p.add_argument("--fix-gaps", action="store_true", help="Auto-fix gaps after ASR")
    p.add_argument("--max-gap", type=float, default=2.0, help="Max gap to fix (seconds)")
    p.set_defaults(func=cmd_transcribe)

    # fix-gaps
    p = subparsers.add_parser("fix-gaps", help="Fix gaps in an SRT file")
    p.add_argument("srt", help="Input SRT file")
    p.add_argument("--max-gap", type=float, default=2.0, help="Max gap to fix (seconds)")
    p.add_argument("--output", "-o", help="Output SRT file (default: overwrite input)")
    p.set_defaults(func=cmd_fix_gaps)

    # validate
    p = subparsers.add_parser("validate", help="Validate SRT file format")
    p.add_argument("srt", help="Input SRT file")
    p.set_defaults(func=cmd_validate)

    # info
    p = subparsers.add_parser("info", help="Show SRT file statistics")
    p.add_argument("srt", help="Input SRT file")
    p.set_defaults(func=cmd_info)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
