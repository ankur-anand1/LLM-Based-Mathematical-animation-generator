"""Visual quality check: look at a rendered frame and flag layout problems.

This catches the failures that execution logs cannot: animations that render
'successfully' but look wrong (overlapping text, off-screen elements, blank
frames). A vision model judges a sampled frame and reports problems so the
generator can fix the code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .config import Config
from .llm_client import LLMClient


def _ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for found in base.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"):
        return str(found)
    return None


def extract_frame(video_path: Path, seconds_before_end: float = 2.0) -> Path | None:
    """Grab one frame near the end of the video (where the full scene is visible)."""
    ff = _ffmpeg()
    if ff is None:
        return None
    out = Path(video_path).with_name(Path(video_path).stem + "_qa.png")
    cmd = [ff, "-y", "-sseof", f"-{seconds_before_end}", "-i", str(video_path),
           "-frames:v", "1", str(out)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None
    return out if (proc.returncode == 0 and out.exists()) else None


def check_frame(image_path: Path, concept: str, config: Config | None = None) -> tuple[bool, str]:
    """Return (is_ok, feedback). is_ok=True means no serious visual problems."""
    config = config or Config.load()
    client = LLMClient(config)
    question = (
        f"This is a frame from an educational animation about: {concept}.\n"
        "Check ONLY for serious visual problems:\n"
        "1) elements overlapping so much they are unreadable,\n"
        "2) text or objects cut off or outside the frame,\n"
        "3) the frame is essentially blank/empty.\n"
        "If the frame is acceptable, reply with exactly: GOOD\n"
        "Otherwise reply with: PROBLEM: <one short sentence describing the worst issue>"
    )
    answer = client.describe_image(question, str(image_path))
    is_ok = answer.strip().upper().startswith("GOOD")
    return is_ok, answer.strip()


def extract_frames(video_path: Path, offsets=(1.0, 3.0, 6.0)) -> list[Path]:
    """Grab several frames at different times near the end of the video."""
    ff = _ffmpeg()
    if ff is None:
        return []
    frames: list[Path] = []
    for i, off in enumerate(offsets):
        out = Path(video_path).with_name(Path(video_path).stem + f"_qa{i}.png")
        cmd = [ff, "-y", "-sseof", f"-{off}", "-i", str(video_path),
               "-frames:v", "1", str(out)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            continue
        if proc.returncode == 0 and out.exists():
            frames.append(out)
    return frames


def visual_review(video_path: Path, concept: str,
                  config: Config | None = None) -> tuple[bool, str]:
    """Check multiple frames; fail if ANY frame has a serious problem.

    Sampling several moments catches problems that only appear partway through
    the animation (mid-motion overlaps, elements leaving the frame, etc.).
    """
    frames = extract_frames(Path(video_path))
    if not frames:
        # Cannot check (no ffmpeg) -> don't block the pipeline.
        return True, "skipped (no frame)"
    for frame in frames:
        ok, feedback = check_frame(frame, concept, config=config)
        if not ok:
            return False, feedback
    return True, "GOOD"
