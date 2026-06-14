"""SRT manipulation utilities: gap fixing, merging, renumbering, format checking."""

import re
from pathlib import Path
from typing import Optional


def fmt_ms(ms: int) -> str:
    """Format milliseconds to SRT timestamp: HH:MM:SS,mmm"""
    h, remainder = divmod(ms, 3600000)
    m, remainder = divmod(remainder, 60000)
    s, ms_remainder = divmod(remainder, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_remainder:03d}"


def parse_ts(ts_str: str) -> Optional[int]:
    """Parse SRT timestamp to milliseconds.

    >>> parse_ts("00:01:23,456")
    83456
    """
    m = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", ts_str.strip())
    if not m:
        return None
    return (int(m[1]) * 3600000 + int(m[2]) * 60000
            + int(m[3]) * 1000 + int(m[4]))


def parse_srt(path: str | Path) -> list[dict]:
    """Parse an SRT file into a list of block dicts.

    Each block: {'index': int, 't1': int, 't2': int, 'text': list[str]}
    """
    content = Path(path).read_text(encoding="utf-8")
    blocks_raw = content.strip().split("\n\n")
    blocks = []
    for block in blocks_raw:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        # Optional: first line might be a number
        ts_line_idx = 0 if re.match(r"\d+$", lines[0]) else 0
        m = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
            lines[1] if ts_line_idx == 0 else lines[0]
        )
        if not m:
            # Try without index line
            m = re.match(
                r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                lines[0]
            )
            if not m:
                continue
            text_start = 1
        else:
            text_start = 2 if ts_line_idx == 0 else 1

        t1, t2 = parse_ts(m[1]), parse_ts(m[2])
        text_lines = [l for l in lines[text_start:] if l.strip()]
        if not text_lines:
            continue
        blocks.append({"t1": t1, "t2": t2, "text": text_lines})
    return blocks


def write_srt(blocks: list[dict], output_path: str | Path) -> Path:
    """Write a list of block dicts to an SRT file with sequential numbering."""
    output_path = Path(output_path)
    out_lines = []
    for i, b in enumerate(blocks):
        out_lines.append(f"{i + 1}")
        out_lines.append(f"{fmt_ms(b['t1'])} --> {fmt_ms(b['t2'])}")
        out_lines.extend(b["text"])
        out_lines.append("")
    output_path.write_text("\n".join(out_lines), encoding="utf-8")
    return output_path


def fix_gaps(input_path: str | Path, max_gap_s: float = 2.0,
             output_path: Optional[str | Path] = None) -> dict:
    """Extend subtitle end times to close small gaps between blocks.

    Any gap between 0 and max_gap_s is closed by extending the previous
    block's end to 80ms before the next block's start.

    Returns {'blocks': int, 'fixed': int}.
    """
    blocks = parse_srt(input_path)
    max_gap_ms = int(max_gap_s * 1000)
    fixed = 0

    for i in range(len(blocks) - 1):
        gap_ms = blocks[i + 1]["t1"] - blocks[i]["t2"]
        if 0 < gap_ms < max_gap_ms:
            new_end = blocks[i + 1]["t1"] - 80
            if new_end > blocks[i]["t1"]:
                blocks[i]["t2"] = new_end
                fixed += 1

    write_srt(blocks, output_path or input_path)
    return {"blocks": len(blocks), "fixed": fixed}


def merge_chunks(chunk_dir: str | Path, output_path: str | Path,
                 chunk_duration_s: int = 600) -> Path:
    """Merge multiple chunk SRT files with time offset corrections.

    Each chunk file should be named {base}.srt where base matches the
    chunk naming pattern. Time offsets are added incrementally.
    """
    chunk_dir = Path(chunk_dir)
    output_path = Path(output_path)

    srt_files = sorted(chunk_dir.glob("*.srt"))
    all_blocks = []
    for i, srt_file in enumerate(srt_files):
        offset_ms = i * chunk_duration_s * 1000
        blocks = parse_srt(srt_file)
        for b in blocks:
            b["t1"] += offset_ms
            b["t2"] += offset_ms
        all_blocks.extend(blocks)

    return write_srt(all_blocks, output_path)


def remove_empty_blocks(input_path: str | Path,
                        output_path: Optional[str | Path] = None) -> dict:
    """Remove blocks with empty text content and renumber."""
    blocks = parse_srt(input_path)
    blocks = [b for b in blocks if any(line.strip() for line in b["text"])]
    write_srt(blocks, output_path or input_path)
    return {"blocks_before": len(blocks), "removed": 0}  # simplified


def count_blocks(input_path: str | Path) -> int:
    """Count blocks in an SRT file."""
    return len(parse_srt(input_path))


def validate_srt(input_path: str | Path) -> list[str]:
    """Validate SRT file format. Returns list of issues found (empty = clean)."""
    issues = []
    blocks = parse_srt(input_path)

    for i, b in enumerate(blocks):
        if b["t1"] >= b["t2"]:
            issues.append(f"Block {i + 1}: start >= end")
        if i > 0 and b["t1"] < blocks[i - 1]["t2"]:
            issues.append(f"Block {i + 1}: overlaps previous block")
        char_count = sum(len(line) for line in b["text"])
        if char_count > 80:
            issues.append(f"Block {i + 1}: {char_count} chars (recommended max 80)")

    return issues
