"""Orchestrates the full pipeline: prompt -> LLM code -> render -> self-repair.

This module is the heart of the system and the part you measure for the paper
(success rate, number of repair attempts needed, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .llm_client import LLMClient
from .prompts import (
    build_blueprint_messages,
    build_generation_messages,
    build_repair_messages,
    build_visual_fix_messages,
)
from .renderer import render_code


@dataclass
class GenerationResult:
    success: bool
    video_path: Path | None
    final_code: str
    attempts: int
    log: list[str] = field(default_factory=list)


def generate_animation(
    user_prompt: str,
    config: Config | None = None,
    progress=lambda msg: None,
) -> GenerationResult:
    """Generate and render an animation from a natural-language prompt.

    `progress` is an optional callback(str) so a UI can show live status.
    """
    config = config or Config.load()
    client = LLMClient(config)
    log: list[str] = []

    def note(msg: str) -> None:
        log.append(msg)
        progress(msg)

    note("Generating Manim code from your prompt...")
    code = client.complete(build_generation_messages(user_prompt))

    last_error = ""
    for attempt in range(1, config.max_repair_attempts + 1):
        note(f"Rendering (attempt {attempt})...")
        result = render_code(code, quality=config.quality)

        if result.success:
            note("Render succeeded.")
            return GenerationResult(
                success=True,
                video_path=result.video_path,
                final_code=code,
                attempts=attempt,
                log=log,
            )

        last_error = result.error or "unknown error"
        note(f"Render failed: {last_error.splitlines()[-1] if last_error else ''}")

        if attempt < config.max_repair_attempts:
            note("Asking the model to fix the code...")
            code = client.complete(
                build_repair_messages(user_prompt, code, last_error)
            )

    note("Gave up after maximum repair attempts.")
    return GenerationResult(
        success=False,
        video_path=None,
        final_code=code,
        attempts=config.max_repair_attempts,
        log=log,
    )


def generate_from_blueprint(
    blueprint: str,
    config: Config | None = None,
    progress=lambda msg: None,
    context: str = "",
    visual_check: bool = False,
    concept: str = "",
) -> GenerationResult:
    """Generate and render an animation from a structured scene blueprint (JSON).

    One unified loop handles BOTH kinds of failure:
    - render errors  -> Renderer-in-the-loop (RITL) self-correction
    - visual problems -> Visual-QA self-correction (if `visual_check=True`)

    `context` is optional RAG content (motion rules + worked examples).
    `concept` is a short topic description used by the visual check.
    """
    config = config or Config.load()
    client = LLMClient(config)
    log: list[str] = []

    def note(msg: str) -> None:
        log.append(msg)
        progress(msg)

    note("Generating Manim code from the blueprint...")
    code = client.complete(build_blueprint_messages(blueprint, context=context))

    for attempt in range(1, config.max_repair_attempts + 1):
        note(f"Rendering (attempt {attempt})...")
        result = render_code(code, quality=config.quality)

        # 1) Render failed -> fix the code from the error (RITL).
        if not result.success:
            error = result.error or "unknown error"
            note(f"Render failed: {error.splitlines()[-1] if error else ''}")
            if attempt < config.max_repair_attempts:
                note("Asking the model to fix the code (error)...")
                code = client.complete(build_repair_messages(blueprint, code, error))
            continue

        # 2) Render succeeded -> optionally check how it LOOKS.
        if visual_check and attempt < config.max_repair_attempts:
            from .visual_qa import visual_review
            note("Checking the result visually...")
            ok, feedback = visual_review(result.video_path, concept or blueprint[:80],
                                         config=config)
            if not ok:
                note(f"Visual issue: {feedback}")
                note("Asking the model to fix the layout (visual)...")
                code = client.complete(build_visual_fix_messages(blueprint, code, feedback))
                continue
            note("Visual check passed.")

        note("Render succeeded.")
        return GenerationResult(
            success=True,
            video_path=result.video_path,
            final_code=code,
            attempts=attempt,
            log=log,
        )

    note("Gave up after maximum attempts.")
    return GenerationResult(
        success=False,
        video_path=None,
        final_code=code,
        attempts=config.max_repair_attempts,
        log=log,
    )
