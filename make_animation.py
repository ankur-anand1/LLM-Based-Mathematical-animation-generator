"""Full pipeline in ONE program: prompt -> blueprint -> video.

Ask the user for a physics topic, then:
  1. Use Gemini (your friend's object_deducer) to build a structured blueprint.
  2. Use OpenAI + Manim (your part) to generate code and render a video.

Usage:
    python make_animation.py
        -> asks "Enter physics prompt:"
    python make_animation.py "projectile motion"
        -> uses the given topic directly (no question)
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
OD = ROOT / "physisyn2" / "object_deducer"          # your friend's module
DB_PATH = OD / "db" / "phenomena.json"
PROMPT_PATH = OD / "prompts" / "deduce_objects.txt"

# Load both .env files: OpenAI key (root) and Gemini key (object_deducer).
# override=True so the .env files win over any stale system env vars.
load_dotenv(ROOT / ".env", override=True)
load_dotenv(OD / ".env", override=True)

# Make the object_deducer modules importable, then import the Gemini helpers.
sys.path.insert(0, str(OD))
from gemini_client import ask_gemini  # noqa: E402  (needs the env + sys.path above)
from validator import validate        # noqa: E402

# Our own pieces.
from src.config import Config          # noqa: E402
from src.generator import generate_from_blueprint  # noqa: E402
from src.renderer import render_code   # noqa: E402
from src.retrieval import build_rag_context, match_template  # noqa: E402


# ---------------------------------------------------------------------------
# Make sure Manim can find FFmpeg even in an old terminal.
# ---------------------------------------------------------------------------
def ensure_ffmpeg_on_path() -> None:
    if shutil.which("ffmpeg"):
        return
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for exe in base.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"):
        os.environ["PATH"] = str(exe.parent) + os.pathsep + os.environ.get("PATH", "")
        return


# ---------------------------------------------------------------------------
# Stage 1: prompt -> blueprint (Gemini), adapted from object_deducer/main.py
# ---------------------------------------------------------------------------
def retrieve_template(user_prompt: str, db: dict) -> dict:
    """Pick a starter template by simple keyword matching."""
    p = user_prompt.lower()
    if "projectile" in p:
        topic = db["projectile_motion"]
    elif "shm" in p:
        topic = db["shm"]
    elif "resonance" in p:
        topic = db["electrical_resonance"]
    else:
        return {
            "phenomenon": "unknown",
            "objects": [],
            "constraints": [],
            "topics": [],
            "camera": {},
            "text": [],
        }
    return {
        "objects": topic["default_objects"],
        "constraints": topic["default_constraints"],
        "topics": topic["default_topics"],
        "camera": topic["default_camera"],
        "text": topic["default_text"],
    }


def make_blueprint(prompt: str) -> dict:
    """Ask Gemini to expand the prompt + template into a full scene blueprint."""
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    template = retrieve_template(prompt, db)

    final_prompt = (
        f"{PROMPT_PATH.read_text(encoding='utf-8')}\n\n"
        f"USER_PROMPT:\n{prompt}\n\n"
        f"RETRIEVED_SCENE_TEMPLATE:\n{json.dumps(template, indent=2)}"
    )

    raw = ask_gemini(final_prompt).strip()
    if raw.startswith("```json"):
        raw = raw.replace("```json", "").replace("```", "")

    data = json.loads(raw)
    validate(data)
    return data


# ---------------------------------------------------------------------------
# Main: run both stages end to end
# ---------------------------------------------------------------------------
def main() -> int:
    ensure_ffmpeg_on_path()

    # Get the topic: from the command line, or by asking.
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:]).strip()
    else:
        prompt = input("Enter physics prompt: ").strip()

    if not prompt:
        print("No prompt given.")
        return 1

    config = Config.load()

    # ROUTER: if we have a hand-written, tested template for this topic, use it
    # directly. This is the reliable path and needs no API calls at all.
    template = match_template(prompt)
    if template is not None:
        print(f"\n[router] Matched a tested template: {template.name}")
        print("[router] Using the reliable hand-written animation (no AI needed).")
        code = template.read_text(encoding="utf-8")
        result = render_code(code, quality=config.quality)
        if result.success:
            print(f"\nDONE! Video saved at:\n  {result.video_path}")
            return 0
        print(f"[router] Template render failed ({result.error}); falling back to AI.")

    # Otherwise we need both keys for the AI (free-form + RAG) path.
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY missing (physisyn2/object_deducer/.env).")
        return 1
    if not config.is_configured:
        print("ERROR: OPENAI_API_KEY missing (.env in the project root).")
        return 1

    # Stage 1: blueprint.
    print("\n[1/2] Understanding your prompt and building the blueprint (Gemini)...")
    try:
        blueprint = make_blueprint(prompt)
    except Exception as e:  # noqa: BLE001
        print(f"Failed to build blueprint: {e}")
        return 1
    print(f"      Blueprint ready: {blueprint.get('phenomenon', {})}")

    # Stage 2: code + render (with self-repair), boosted with RAG context.
    print("\n[2/2] Generating Manim code and rendering the video (OpenAI + Manim + RAG)...")
    rag_context = build_rag_context(prompt)
    result = generate_from_blueprint(
        json.dumps(blueprint, indent=2),
        config=config,
        progress=lambda m: print(f"      {m}"),
        context=rag_context,
        visual_check=True,
        concept=prompt,
    )

    # Save the blueprint and generated code next to the video for inspection.
    if result.video_path is not None:
        stem = result.video_path.with_suffix("")
        Path(f"{stem}_blueprint.json").write_text(
            json.dumps(blueprint, indent=2), encoding="utf-8"
        )
        Path(f"{stem}.py").write_text(result.final_code, encoding="utf-8")

    if result.success:
        print(f"\nDONE! Video saved at:\n  {result.video_path}")
        print(f"  (Manim code saved next to it as {result.video_path.with_suffix('.py').name})")
        return 0
    print("\nFailed to render the animation after several attempts.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
