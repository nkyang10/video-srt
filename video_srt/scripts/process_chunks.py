#!/usr/bin/env python3
"""Batch process audio chunks with yuesub-api and merge into combined SRT with time offsets."""
import subprocess, sys, os, glob, re
from pathlib import Path

CHUNKS_DIR = os.environ.get("CHUNKS_DIR", "/home/ubuntu/tmp/yuesub_chunks")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/home/ubuntu/tmp/yuesub_output_final")
WORKDIR = os.environ.get("WORKDIR", "/home/ubuntu/tmp/yuesub-api")
CHUNK_DURATION = int(os.environ.get("CHUNK_DURATION", "600"))
YUESUB_PYTHON = os.environ.get("YUESUB_PYTHON", "")

os.makedirs(OUTPUT_DIR, exist_ok=True)
chunks = sorted(glob.glob(os.path.join(CHUNKS_DIR, "chunk_*.wav")))
if not chunks:
    print(f"No chunk_*.wav files found in {CHUNKS_DIR}")
    sys.exit(1)

print(f"Found {len(chunks)} chunks to process")

if YUESUB_PYTHON:
    python_bin = YUESUB_PYTHON
else:
    venv_python = os.path.join(WORKDIR, "venv", "bin", "python3")
    if os.path.exists(venv_python):
        python_bin = venv_python
    else:
        venv_python = os.path.join(WORKDIR, "venv", "bin", "python")
        if os.path.exists(venv_python):
            python_bin = venv_python
        else:
            python_bin = sys.executable

print(f"Using Python: {python_bin}")

combined_path = os.path.join(OUTPUT_DIR, "combined.srt")
if os.path.exists(combined_path):
    os.remove(combined_path)

for i, chunk_path in enumerate(chunks):
    chunk_name = Path(chunk_path).stem
    offset_seconds = i * CHUNK_DURATION

    print(f"\n{'='*60}")
    print(f"Processing chunk {i+1}/{len(chunks)}: {chunk_name}")
    print(f"Time offset: {offset_seconds}s ({offset_seconds//60}m{offset_seconds%60}s)")

    result = subprocess.run(
        [python_bin, "-u", "cli.py", chunk_path,
         "--output-dir", OUTPUT_DIR, "--corrector", "opencc", "--max-length", "8.0"],
        capture_output=True, text=True, timeout=1800, cwd=WORKDIR
    )

    last_lines = result.stdout.strip().splitlines()[-5:] if result.stdout else []
    print("\n".join(last_lines))
    if result.stderr:
        stderr_last = result.stderr.strip().splitlines()[-5:] if result.stderr.strip() else []
        print("STDERR:", "; ".join(stderr_last))

    if result.returncode != 0:
        print(f"ERROR chunk {i+1}: exit code {result.returncode}")
        continue

    srt_path = os.path.join(OUTPUT_DIR, f"{chunk_name}.srt")
    if not os.path.exists(srt_path):
        print(f"No SRT produced for chunk {i+1}")
        continue

    with open(srt_path, 'r', encoding='utf-8') as f:
        srt_content = f.read()

    line_count = len(srt_content.splitlines())
    print(f"Got {line_count} lines of SRT")

    with open(combined_path, 'a', encoding='utf-8') as out:
        for line in srt_content.splitlines():
            match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})', line)
            if match:
                h1, m1, s1, ms1 = int(match[1]), int(match[2]), int(match[3]), int(match[4])
                h2, m2, s2, ms2 = int(match[5]), int(match[6]), int(match[7]), int(match[8])
                t1 = (h1*3600 + m1*60 + s1) * 1000 + ms1 + offset_seconds * 1000
                t2 = (h2*3600 + m2*60 + s2) * 1000 + ms2 + offset_seconds * 1000
                out.write(f"{t1//3600000:02d}:{(t1%3600000)//60000:02d}:{(t1%60000)//1000:02d},{t1%1000:03d} --> {t2//3600000:02d}:{(t2%3600000)//60000:02d}:{(t2%60000)//1000:02d},{t2%1000:03d}\n")
            elif line.strip():
                out.write(f"{line}\n")
            else:
                out.write("\n")

print(f"\n{'='*60}")
print(f"Done! Combined SRT: {combined_path}")
