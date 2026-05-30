"""Runs Manim on generated code and returns the rendered video path."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from .prompts import SCENE_CLASS_NAME

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


@dataclass
class RenderResult:
    success: bool
    video_path: Path | None
    error: str | None


# Lightweight guard against obviously unsafe generated code. This is NOT a real
# sandbox; for production you would render inside a container or restricted VM.
_FORBIDDEN = ("import os", "import sys", "subprocess", "open(", "eval(", "exec(",
              "__import__", "socket", "requests", "urllib")


def looks_unsafe(code: str) -> str | None:
    for token in _FORBIDDEN:
        if token in code:
            return f"Refusing to run: generated code contains '{token}'."
    return None


def render_code(code: str, quality: str = "m") -> RenderResult:
    """Write code to a temp file and invoke Manim as a subprocess.

    quality: 'l' (480p), 'm' (720p), or 'h' (1080p).
    """
    unsafe = looks_unsafe(code)
    if unsafe:
        return RenderResult(success=False, video_path=None, error=unsafe)

    OUTPUT_DIR.mkdir(exist_ok=True)
    run_id = uuid.uuid4().hex[:8]

    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / f"scene_{run_id}.py"
        script_path.write_text(code, encoding="utf-8")

        quality_flag = {"l": "-ql", "m": "-qm", "h": "-qh"}.get(quality, "-qm")
        final_video = OUTPUT_DIR / f"animation_{run_id}.mp4"

        cmd = [
            sys.executable, "-m", "manim", "render",
            quality_flag,
            "--media_dir", tmp,
            "-o", final_video.name,
            "--output_file", str(final_video),
            str(script_path), SCENE_CLASS_NAME,
        ]

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired:
            return RenderResult(False, None, "Rendering timed out after 600s.")

        if proc.returncode != 0:
            error = (proc.stderr or proc.stdout or "Unknown render error").strip()
            return RenderResult(False, None, error[-4000:])  # tail of the log

        found = _locate_video(Path(tmp), final_video)
        if found is None:
            return RenderResult(False, None, "Render reported success but no video found.")
        return RenderResult(True, found, None)


def _locate_video(media_dir: Path, preferred: Path) -> Path | None:
    """Find the produced mp4. Manim's output location varies by version/flags."""
    if preferred.exists():
        return preferred
    candidates = sorted(
        media_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if candidates:
        target = preferred
        target.write_bytes(candidates[0].read_bytes())
        return target
    return None
