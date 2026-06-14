#!/usr/bin/env python3
"""Fix VAD subtitle gaps: extend each subtitle's end to 80ms before next starts.

Usage:
  python3 fix_subtitle_gaps.py input.srt [--max-gap 2.0] [--output output.srt]
"""
import re, sys


def fmt_ms(ms):
    return f"{ms//3600000:02d}:{(ms%3600000)//60000:02d}:{(ms%60000)//1000:02d},{ms%1000:03d}"


def parse_ts(ts_str):
    m = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', ts_str.strip())
    if not m:
        return None
    return int(m[1])*3600000 + int(m[2])*60000 + int(m[3])*1000 + int(m[4])


def fix_gaps(input_path, max_gap_s=2.0, output_path=None):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks_raw = content.strip().split('\n\n')
    blocks = []
    for block in blocks_raw:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        m = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', lines[1])
        if not m:
            continue
        t1, t2 = parse_ts(m[1]), parse_ts(m[2])
        text_lines = [l for l in lines[2:] if l.strip()]
        if not text_lines:
            continue
        blocks.append({'t1': t1, 't2': t2, 'text': text_lines})
    max_gap_ms = int(max_gap_s * 1000)
    fixed = 0
    for i in range(len(blocks) - 1):
        gap_ms = blocks[i+1]['t1'] - blocks[i]['t2']
        if 0 < gap_ms < max_gap_ms:
            new_end = blocks[i+1]['t1'] - 80
            if new_end > blocks[i]['t1']:
                blocks[i]['t2'] = new_end
                fixed += 1
    out_lines = []
    for i, b in enumerate(blocks):
        new_ts = f"{fmt_ms(b['t1'])} --> {fmt_ms(b['t2'])}"
        out_lines.append(f"{i+1}\n{new_ts}\n" + '\n'.join(b['text']))
    result = '\n\n'.join(out_lines)
    with open(output_path or input_path, 'w', encoding='utf-8') as f:
        f.write(result)
    return {'blocks': len(blocks), 'fixed': fixed}


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print("Usage: fix_subtitle_gaps.py <input.srt> [--max-gap 2.0] [--output output.srt]")
        sys.exit(1)
    input_path = args[0]
    max_gap = 2.0
    output_path = None
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == '--max-gap' and i + 1 < len(args):
            max_gap = float(args[i + 1])
            i += 1
        elif arg == '--output' and i + 1 < len(args):
            output_path = args[i + 1]
            i += 1
        i += 1
    result = fix_gaps(input_path, max_gap, output_path)
    print(f"Fixed {result['fixed']} gaps in {result['blocks']} blocks")
