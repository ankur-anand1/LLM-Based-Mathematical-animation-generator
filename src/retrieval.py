"""Router + RAG retrieval for the hybrid animation pipeline.

Two jobs:
1. ROUTER  -> if the prompt matches a hand-written, tested template, use it
              directly (the reliable path).
2. RAG     -> otherwise, retrieve the most relevant tested example(s) and a set
              of motion rules, to inject into the free-form code-generation
              prompt so the model produces real animations (not static pictures).
"""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Keyword -> template file. The first matching keyword wins.
TEMPLATE_KEYWORDS: dict[str, str] = {
    "projectile": "projectile.py",
    "parabola": "projectile.py",
    "rocket": "rocket.py",
    "propulsion": "rocket.py",
    "thrust": "rocket.py",
    "faraday": "faraday.py",
    "induction": "faraday.py",
    "electromagnetic": "em_wave.py",
    "em wave": "em_wave.py",
    "light wave": "em_wave.py",
    "maxwell": "em_wave.py",
    "shm": "shm.py",
    "simple harmonic": "shm.py",
    "oscillat": "shm.py",
    "spring": "shm.py",
}


def match_template(prompt: str) -> Path | None:
    """Return the path to a tested template if the prompt matches one, else None."""
    p = prompt.lower()
    for keyword, filename in TEMPLATE_KEYWORDS.items():
        if keyword in p:
            path = TEMPLATES_DIR / filename
            if path.exists():
                return path
    return None


MOTION_RULES = """CRITICAL ANIMATION RULES (these are the most common mistakes - avoid them):
- This is an ANIMATION, not a static diagram. The key objects MUST MOVE over time.
- To animate continuous motion, use a ValueTracker as a clock plus `always_redraw`,
  so objects are redrawn each frame at their new position. Pattern:
      t = ValueTracker(0)
      dot = always_redraw(lambda: Dot(axes.c2p(t.get_value(), f(t.get_value()))))
      self.add(dot)
      self.play(t.animate.set_value(T_MAX), run_time=8, rate_func=linear)
- Oscillation: position = A*cos(omega*t). Projectile: x=vx*t, y=vy*t-0.5*g*t**2.
- Use TracedPath(point_func) to draw a curve as something moves.
- Do NOT just Create() a pile of static shapes/arrows and then FadeOut them.
  Show the actual physical motion the concept is about.
- Keep elements spaced out: nothing overlapping, nothing off-screen.
"""


def _rank_examples(prompt: str) -> list[str]:
    """Pick the most relevant template filenames for the prompt (simple keyword RAG)."""
    p = prompt.lower()
    ranked: list[str] = []

    oscillation_words = ["oscillat", "shm", "spring", "pendulum",
                         "vibrat", "periodic", "harmonic"]
    trajectory_words = ["projectile", "trajectory", "parabola", "throw",
                        "launch", "gravity", "ball", "fall"]
    em_words = ["electro", "magnet", "induction", "faraday", "field", "charge",
                "current", "wave", "light", "flux", "maxwell"]

    if any(w in p for w in em_words):
        ranked.append("em_wave.py")
    if any(w in p for w in oscillation_words):
        ranked.append("shm.py")
    if any(w in p for w in trajectory_words):
        ranked.append("projectile.py")
    if not ranked:
        ranked.append("shm.py")  # default: a clear motion example

    # de-duplicate while keeping order
    seen: set[str] = set()
    return [x for x in ranked if not (x in seen or seen.add(x))]


def retrieve_examples(prompt: str, max_examples: int = 1) -> list[str]:
    """Return tested example code (as text) most relevant to the prompt."""
    examples: list[str] = []
    for filename in _rank_examples(prompt)[:max_examples]:
        path = TEMPLATES_DIR / filename
        if path.exists():
            examples.append(path.read_text(encoding="utf-8"))
    return examples


def _semantic_examples(prompt: str, k: int = 1) -> list[str]:
    """Try the semantic (embeddings) index; return [] if unavailable."""
    try:
        from .rag_index import semantic_search
        hits = semantic_search(prompt, k=k)
        return [h["code"] for h in hits]
    except Exception:
        return []


def build_rag_context(prompt: str, use_semantic: bool = True) -> str:
    """Build the extra prompt context (motion rules + a worked example) for RAG.

    Prefers semantic search (works for ANY topic); falls back to keyword matching
    over the local templates if embeddings are unavailable.
    """
    examples = _semantic_examples(prompt) if use_semantic else []
    if not examples:
        examples = retrieve_examples(prompt)

    parts = [MOTION_RULES]
    for example in examples:
        parts.append(
            "Here is a COMPLETE, CORRECT example animation in the required style. "
            "Learn its motion patterns (ValueTracker + always_redraw + TracedPath) "
            "and apply the same techniques to the new scene. Do not copy it blindly:\n"
            f"```python\n{example}\n```"
        )
    return "\n\n".join(parts)
