"""ASR engine selection and execution for the video-srt pipeline.

Two backends:
  1. SenseVoiceSmall (via yuesub-api) — fast, speech-optimized (~30x realtime)
  2. faster-whisper large-v3-turbo — fallback for music/singing content

Decision rule: try SenseVoiceSmall first. If VAD returns zero segments,
fall back to faster-whisper automatically.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_sensevoice_asr(audio_path: str | Path,
                       workdir: str | Path = "/tmp/yuesub-api",
                       output_dir: str | Path = "/tmp/yuesub_output",
                       max_length: float = 8.0,
                       corrector: str = "opencc") -> Optional[Path]:
    """Run SenseVoiceSmall ASR via yuesub-api cli.py.

    Returns path to generated SRT, or None if VAD produced zero segments.

    Required setup:
      git clone https://github.com/hon9kon9ize/yuesub-api.git {workdir}
      cd {workdir} && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

    Note: patch transcriber/AutoTranscriber.py to use HuggingFace hub:
      model="FunAudioLLM/SenseVoiceSmall"
      hub="hf"
    """
    audio_path = Path(audio_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    workdir = Path(workdir)
    venv_python = workdir / "venv" / "bin" / "python3"
    if not venv_python.exists():
        venv_python = workdir / "venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = Path(sys.executable)

    result = subprocess.run(
        [str(venv_python), "-u", "cli.py", str(audio_path),
         "--output-dir", str(output_dir), "--corrector", corrector,
         "--max-length", str(max_length)],
        capture_output=True, text=True, timeout=1800, cwd=str(workdir)
    )

    if "No transcriptions found" in result.stdout:
        return None

    # Find the generated SRT
    base_name = audio_path.stem
    srt_path = output_dir / f"{base_name}.srt"
    if srt_path.exists() and srt_path.stat().st_size > 0:
        return srt_path

    # Fallback: find any .srt file in output dir
    srt_files = list(output_dir.glob("*.srt"))
    if srt_files:
        return max(srt_files, key=lambda p: p.stat().st_size)

    return None


def run_faster_whisper_asr(audio_path: str | Path,
                           language: Optional[str] = None,
                           output_srt: Optional[str | Path] = None,
                           model_name: str = "large-v3-turbo",
                           beam_size: int = 5) -> Path:
    """Run faster-whisper ASR on audio file.

    Returns path to generated SRT file.
    Requires: pip install faster-whisper
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper not installed. Run: pip install faster-whisper"
        )

    audio_path = Path(audio_path)
    if output_srt is None:
        output_srt = audio_path.with_suffix(".srt")

    model = WhisperModel(model_name, device="cpu", compute_type="int8")

    kwargs = dict(
        beam_size=beam_size,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    if language:
        kwargs["language"] = language

    segments, info = model.transcribe(str(audio_path), **kwargs)

    # Write SRT
    lines = []
    for i, seg in enumerate(segments, 1):
        start_ms = int(seg.start * 1000)
        end_ms = int(seg.end * 1000)
        lines.append(f"{i}")
        lines.append(
            f"{start_ms//3600000:02d}:{(start_ms%3600000)//60000:02d}:"
            f"{(start_ms%60000)//1000:02d},{start_ms%1000:03d} --> "
            f"{end_ms//3600000:02d}:{(end_ms%3600000)//60000:02d}:"
            f"{(end_ms%60000)//1000:02d},{end_ms%1000:03d}"
        )
        lines.append(seg.text.strip())
        lines.append("")

    Path(output_srt).write_text("\n".join(lines), encoding="utf-8")
    return Path(output_srt)


def transcribe(audio_path: str | Path,
               language: Optional[str] = None,
               workdir: str | Path = "/tmp/yuesub-api",
               output_dir: str | Path = "/tmp/yuesub_output") -> Path:
    """Auto-select ASR backend and transcribe audio to SRT.

    Tries SenseVoiceSmall first. Falls back to faster-whisper if VAD
    produces zero segments (commonly happens with music/singing content).

    Returns path to generated SRT.
    """
    # Try SenseVoiceSmall first (fast path)
    srt_path = run_sensevoice_asr(audio_path, workdir=workdir, output_dir=output_dir)

    if srt_path is not None:
        print(f"SenseVoiceSmall ASR: {srt_path}")
        return srt_path

    # Fallback to faster-whisper
    print("SenseVoiceSmall VAD returned zero segments. "
          "Falling back to faster-whisper...")
    srt_path = run_faster_whisper_asr(audio_path, language=language)
    print(f"faster-whisper ASR: {srt_path}")
    return srt_path
