"""Prompt templates that steer the LLM toward valid Manim code.

Keeping prompts in one place makes prompt-engineering experiments (a core part
of the research evaluation) easy to run and document.
"""

SCENE_CLASS_NAME = "GeneratedScene"

SYSTEM_PROMPT = f"""You are an expert Python developer specialised in the Manim \
Community Edition animation library (import with `from manim import *`).

Your job: turn a natural-language description of a mathematical concept into a \
single, self-contained, runnable Manim scene.

Strict rules:
1. Output ONLY Python code. No markdown fences, no prose, no explanation.
2. Start the file with `from manim import *`.
3. Define exactly ONE Scene subclass named `{SCENE_CLASS_NAME}`.
4. Put all animation logic inside its `construct(self)` method.
5. Use only stable, documented Manim Community v0.18 APIs. Avoid deprecated names.
6. Keep the animation under ~20 seconds and visually clear (label things, pace \
   with self.wait()).
7. Do not read files, access the network, or use os/sys/subprocess.
7b. Use ONLY valid Manim color names (e.g. RED, BLUE, GREEN, YELLOW, ORANGE, \
   PURPLE, PINK, TEAL, GREY/GRAY, WHITE, BLACK, GOLD, MAROON). Do NOT invent \
   colors like BROWN or SILVER. Call every function with the correct number of \
   arguments.
8. LaTeX is NOT installed. Do NOT use MathTex, Tex, or any LaTeX-based mobject. \
   Use Text(...) for everything, including formulas (e.g. Text("F = m a") or \
   Text("A = pi r^2")). Use MarkupText only for simple styling, never LaTeX.
9. LAYOUT (very important for clarity):
   - Never stack labels and shapes on top of each other. Give every element a \
     distinct position with generous spacing.
   - Place a label next to its object with `.next_to(obj, DIRECTION, buff=0.3)`, \
     not on top of it.
   - Group related items and space them with `VGroup(...).arrange(DOWN, buff=0.5)`.
   - Keep the title at the top edge and body content clearly below it.
   - Keep everything inside the frame (x in about [-7,7], y in about [-4,4]).
   - Fade out old elements before introducing a new cluster, so the screen is \
     never crowded.
10. USE ONLY REAL MANIM API (do not invent classes or arguments):
   - For curves/paths use: ArcBetweenPoints(start, end), CurvedArrow(start, end), \
     Arc, Line, Arrow, or VMobject().set_points_smoothly([p1, p2, p3]).
   - Do NOT use QuadraticBezier, CubicBezier, Bezier, or a `path=` keyword \
     argument anywhere -- they DO NOT EXIST and will crash.
   - To move an object along a curve use MoveAlongPath(mobject, path_vmobject).
   - For a magnetic/electric field use arrows (Arrow / Vector) arranged in a \
     pattern; do not invent a field class.
   - If unsure whether something exists, use the simplest primitive (Line, \
     Arrow, Circle, Dot, Text) instead of guessing.
"""

FEW_SHOT_EXAMPLE = f'''from manim import *


class {SCENE_CLASS_NAME}(Scene):
    def construct(self):
        title = Text("Area of a Circle").to_edge(UP)
        self.play(Write(title))

        circle = Circle(radius=2, color=BLUE)
        self.play(Create(circle))

        formula = Text("A = pi r^2").next_to(circle, DOWN)
        self.play(Write(formula))
        self.wait(2)
'''


def build_generation_messages(user_prompt: str) -> list[dict]:
    """Messages for the first attempt at generating a scene."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Here is an example of the exact format expected:\n\n"
            + FEW_SHOT_EXAMPLE,
        },
        {"role": "assistant", "content": "Understood. I will output only code."},
        {
            "role": "user",
            "content": f"Create a Manim animation for: {user_prompt}",
        },
    ]


def build_blueprint_messages(blueprint: str, context: str = "") -> list[dict]:
    """Messages that turn a structured scene blueprint (JSON) into Manim code.

    The blueprint comes from the 'object_deducer' stage: it lists the objects,
    their relationships, constraints, camera plan, and explanatory text for a
    physics/math concept. This is the bridge between the planning stage and the
    rendering stage.

    `context` is optional RAG content (motion rules + a worked example) that is
    prepended to teach the model correct animation patterns.
    """
    instruction = (
        "Create a Manim animation that visualizes the following scene blueprint.\n"
        "The blueprint (JSON) describes the objects, their relationships, "
        "constraints, camera plan, and explanatory text for a concept.\n\n"
        "Guidelines:\n"
        "- Visually represent each object listed in the blueprint.\n"
        "- Show short titles/labels for key explanatory text (keep text brief).\n"
        "- Lay elements out with clear spacing: nothing overlapping, nothing "
        "off-screen (respect a margin from the edges).\n"
        "- Animate in a logical order and use self.wait() for pacing.\n"
        "- Keep the whole animation under about 25 seconds.\n\n"
        f"BLUEPRINT (JSON):\n{blueprint}"
    )
    if context:
        instruction = context + "\n\n" + instruction
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Here is an example of the exact format expected:\n\n"
            + FEW_SHOT_EXAMPLE,
        },
        {"role": "assistant", "content": "Understood. I will output only code."},
        {"role": "user", "content": instruction},
    ]


def build_visual_fix_messages(request: str, code: str, feedback: str) -> list[dict]:
    """Ask the model to fix a layout/visual problem found by the visual-QA check.

    The code renders fine but LOOKS wrong (overlap / off-screen / blank). We feed
    back what the vision model saw and ask for corrected code.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"The original request was: {request}\n\n"
                "The following Manim code renders without errors, but a visual "
                "review of the result found this problem:\n\n"
                f"VISUAL PROBLEM: {feedback}\n\n"
                f"```python\n{code}\n```\n\n"
                "Fix ONLY the layout/visual issue (reposition or resize elements, "
                "add spacing, keep everything inside the frame, avoid overlap). "
                "Keep the animation and its motion the same. Output ONLY the "
                "corrected, complete Python file."
            ),
        },
    ]


def build_repair_messages(user_prompt: str, broken_code: str, error: str) -> list[dict]:
    """Messages that ask the LLM to fix code that failed to render.

    This self-correction loop is the key reliability mechanism of the system.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"The original request was: {user_prompt}\n\n"
                "The following Manim code failed to render:\n\n"
                f"```python\n{broken_code}\n```\n\n"
                f"The error/traceback was:\n\n```\n{error}\n```\n\n"
                "Fix the code so it renders successfully. Output ONLY the "
                "corrected, complete Python file."
            ),
        },
    ]
