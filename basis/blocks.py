"""Composable Manim building blocks.

Convention
----------
- A single shared clock lives in `ctx["tracker"]` (a ValueTracker holding time).
- Optional shared `ctx["axes"]` lets graph-style blocks share one coordinate frame.
- Every block adds animated mobjects via `always_redraw`, so they move when the
  clock advances. Call `run_time(scene, ctx, duration)` once at the end to play.

This is the RELIABLE, hand-written motion layer. The LLM only has to *choose and
arrange* these blocks, not invent the (hard) animation math itself.
"""

from manim import *
import numpy as np


# ---------------------------------------------------------------------------
# Context + lifecycle
# ---------------------------------------------------------------------------
def new_context(t_max: float = 12.0) -> dict:
    """Create the shared state every block reads from."""
    return {"tracker": ValueTracker(0.0), "axes": None, "t_max": t_max}


def run_time(scene, ctx: dict, duration: float = 8.0) -> None:
    """Advance the shared clock from 0 to t_max over `duration` seconds."""
    scene.play(
        ctx["tracker"].animate.set_value(ctx["t_max"]),
        run_time=duration,
        rate_func=linear,
    )
    scene.wait(0.5)


# ---------------------------------------------------------------------------
# Text blocks
# ---------------------------------------------------------------------------
def add_title(scene, ctx, text: str, font_size: int = 40):
    title = Text(text, font_size=font_size).to_edge(UP)
    scene.play(Write(title))
    return title


def add_caption(scene, ctx, text: str, font_size: int = 22):
    caption = Text(text, font_size=font_size).to_edge(DOWN)
    scene.play(FadeIn(caption))
    return caption


# ---------------------------------------------------------------------------
# Coordinate frame
# ---------------------------------------------------------------------------
def add_axes(scene, ctx, x_range=(0, 12, 2), y_range=(-2, 2, 1),
             x_length=5.0, y_length=3.0, corner=RIGHT):
    axes = Axes(
        x_range=list(x_range), y_range=list(y_range),
        x_length=x_length, y_length=y_length, tips=False,
        axis_config={"color": GREY_B, "stroke_width": 2},
    ).to_edge(corner)
    ctx["axes"] = axes
    scene.play(Create(axes))
    return axes


# ---------------------------------------------------------------------------
# Motion blocks
# ---------------------------------------------------------------------------
def add_oscillator(scene, ctx, equilibrium=(-2.5, 0), amplitude=1.8, omega=1.6,
                   color=BLUE):
    """A mass on a spring oscillating horizontally about an equilibrium point."""
    t = ctx["tracker"]
    eq_x, eq_y = equilibrium
    wall_x = eq_x - amplitude - 1.6

    def mass_x():
        return eq_x + amplitude * np.cos(omega * t.get_value())

    wall = Line([wall_x, eq_y - 1, 0], [wall_x, eq_y + 1, 0], color=GREY, stroke_width=6)
    mass = always_redraw(lambda: Square(side_length=0.7, color=color, fill_opacity=0.85)
                         .move_to([mass_x(), eq_y, 0]))
    spring = always_redraw(lambda: _zigzag([wall_x, eq_y, 0], [mass_x() - 0.35, eq_y, 0]))

    scene.play(Create(wall))
    scene.play(Create(spring), Create(mass))
    return VGroup(wall, spring, mass)


def add_pendulum(scene, ctx, pivot=(0, 2), length=2.5, max_angle=0.5, omega=2.0,
                 color=RED):
    """A pendulum bob swinging on an arc (correct geometry: x=L sin, y=-L cos)."""
    t = ctx["tracker"]
    px, py = pivot

    def angle():
        return max_angle * np.cos(omega * t.get_value())

    def bob_point():
        a = angle()
        return [px + length * np.sin(a), py - length * np.cos(a), 0]

    pivot_dot = Dot([px, py, 0], color=GREY, radius=0.08)
    string = always_redraw(lambda: Line([px, py, 0], bob_point(), color=WHITE))
    bob = always_redraw(lambda: Dot(bob_point(), color=color, radius=0.22))

    scene.play(Create(pivot_dot))
    scene.add(string, bob)
    return VGroup(pivot_dot, string, bob)


def add_projectile(scene, ctx, axes=None, v0=7.0, angle_deg=60.0, g=9.8,
                   color=BLUE):
    """A ball launched at an angle, arcing under gravity (on shared axes)."""
    t = ctx["tracker"]
    axes = axes or ctx["axes"]
    vx = v0 * np.cos(np.radians(angle_deg))
    vy = v0 * np.sin(np.radians(angle_deg))

    def point():
        time = t.get_value()
        x = vx * time
        y = max(vy * time - 0.5 * g * time * time, 0)
        return axes.c2p(x, y)

    ball = always_redraw(lambda: Dot(point(), color=color, radius=0.12))
    path = TracedPath(point, stroke_color=YELLOW, stroke_width=3)
    scene.add(path, ball)
    return VGroup(ball, path)


def add_phasor(scene, ctx, center=(-3.5, 0), radius=1.2, omega=1.5, color=GREEN):
    """A rotating vector (phasor) on a circle."""
    t = ctx["tracker"]
    cx, cy = center

    circle = Circle(radius=radius, color=GREY_D).move_to([cx, cy, 0])

    def tip():
        a = omega * t.get_value()
        return [cx + radius * np.cos(a), cy + radius * np.sin(a), 0]

    arrow = always_redraw(lambda: Arrow([cx, cy, 0], tip(), color=color, buff=0))
    scene.play(Create(circle))
    scene.add(arrow)
    return VGroup(circle, arrow)


def add_traveling_wave(scene, ctx, center=(0, -1.5), width=6.0, amplitude=0.8,
                       k=2.0, omega=2.0, color=TEAL):
    """A sine wave that travels (phase moves with the clock)."""
    t = ctx["tracker"]
    cx, cy = center

    def curve():
        return FunctionGraph(
            lambda x: cy + amplitude * np.sin(k * x - omega * t.get_value()),
            x_range=[cx - width / 2, cx + width / 2, 0.05],
            color=color,
        )

    wave = always_redraw(curve)
    scene.add(wave)
    return wave


def add_traced_graph(scene, ctx, func, axes=None, color=RED):
    """Trace y=func(time) on shared axes as the clock advances (e.g. cos)."""
    t = ctx["tracker"]
    axes = axes or ctx["axes"]

    def point():
        x = t.get_value()
        return axes.c2p(x, func(x))

    dot = always_redraw(lambda: Dot(point(), color=color))
    trace = TracedPath(point, stroke_color=color, stroke_width=3)
    scene.add(trace, dot)
    return VGroup(dot, trace)


def add_vector(scene, ctx, start=(0, 0), end=(1, 1), color=YELLOW, label=None):
    """A static labeled vector arrow."""
    arrow = Arrow([*start, 0], [*end, 0], color=color, buff=0)
    group = VGroup(arrow)
    scene.play(GrowArrow(arrow))
    if label:
        tag = Text(label, font_size=22, color=color).next_to(arrow.get_end(), UR, buff=0.1)
        scene.play(FadeIn(tag))
        group.add(tag)
    return group


# ---------------------------------------------------------------------------
# internal helper
# ---------------------------------------------------------------------------
def _zigzag(start, end, coils=12, width=0.3):
    start = np.array(start, dtype=float)
    end = np.array(end, dtype=float)
    span = end - start
    length = float(np.linalg.norm(span))
    if length < 1e-6:
        return VMobject()
    direction = span / length
    normal = np.array([-direction[1], direction[0], 0.0])
    pts = [start]
    segs = coils * 2
    for i in range(1, segs):
        offset = width if i % 2 else -width
        pts.append(start + direction * (length / segs) * i + normal * offset)
    pts.append(end)
    spring = VMobject(color=GREY_B, stroke_width=4)
    spring.set_points_as_corners(pts)
    return spring
