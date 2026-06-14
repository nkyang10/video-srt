"""Audio download and conversion utilities for the video-srt pipeline."""

import subprocess
from pathlib import Path
from typing import Optional


def download_audio(url: str, output_dir: str | Path = "/tmp") -> Path:
    """Download audio from a YouTube URL using yt-dlp.

    Returns path to the downloaded MP3 file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(id)s.%(ext)s")

    result = subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
         "-o", output_template, url],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")

    # Find the downloaded file
    for f in output_dir.iterdir():
        if f.suffix == ".mp3":
            return f
    raise FileNotFoundError(f"No MP3 found in {output_dir}")


def convert_to_wav(input_path: str | Path, output_path: Optional[str | Path] = None,
                   sample_rate: int = 16000, channels: int = 1) -> Path:
    """Convert audio to mono WAV at specified sample rate.

    Default: 16kHz mono (standard for ASR).
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_suffix(".wav")

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_path),
         "-acodec", "pcm_s16le", "-ar", str(sample_rate),
         "-ac", str(channels), str(output_path)],
        capture_output=True, text=True, timeout=300
    )
    return Path(output_path)


def segment_audio(input_path: str | Path, segment_time: int = 600,
                  output_pattern: str = "/tmp/asr_seg_%03d.mp3") -> list[Path]:
    """Segment audio into fixed-duration chunks (default 600s = 10 min).

    Returns list of chunk file paths.
    """
    input_path = Path(input_path)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_path),
         "-f", "segment", "-segment_time", str(segment_time),
         "-c", "copy", output_pattern],
        capture_output=True, text=True, timeout=600
    )

    from pathlib import Path
    pattern = output_pattern.replace("%03d", "*")
    import glob
    return sorted(Path(p) for p in glob.glob(pattern))


def convert_chunks_to_wav(chunk_dir: str | Path = "/tmp/yuesub_chunks",
                           input_pattern: str = "/tmp/asr_seg_*.mp3",
                           sample_rate: int = 16000) -> list[Path]:
    """Convert all MP3 chunks to 16kHz mono WAV files."""
    import glob
    chunk_dir = Path(chunk_dir)
    chunk_dir.mkdir(parents=True, exist_ok=True)

    wav_files = []
    for i, mp3_path in enumerate(sorted(Path(p) for p in glob.glob(input_pattern))):
        wav_path = chunk_dir / f"chunk_{i:03d}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path),
             "-acodec", "pcm_s16le", "-ar", str(sample_rate),
             "-ac", "1", str(wav_path)],
            capture_output=True, text=True, timeout=120
        )
        wav_files.append(wav_path)
    return wav_files


def get_duration_ms(audio_path: str | Path) -> int:
    """Get audio duration in milliseconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio_path)],
        capture_output=True, text=True, timeout=30
    )
    return int(float(result.stdout.strip()) * 1000)
