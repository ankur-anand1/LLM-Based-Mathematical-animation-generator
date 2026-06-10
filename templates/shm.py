"""Hand-written, tested template: Simple Harmonic Motion (SHM).

This is the RELIABLE "template" approach: the motion is written and verified by
a human, so it always looks correct. A mass oscillates on a spring while a
position-vs-time graph is traced in real time.

The Scene is named GeneratedScene so it works with src/renderer.py.
"""

from manim import *
import numpy as np

# --- physics / layout parameters ---
AMPLITUDE = 1.8          # how far the mass swings from equilibrium
OMEGA = 1.6              # angular frequency (speed of oscillation)
WALL_X = -6.0           # x position of the wall
EQUILIBRIUM_X = -2.5    # x position the mass rests at
MASS_HALF = 0.35        # half-width of the mass square
DURATION = 9.0          # seconds of oscillation
T_MAX = DURATION * 1.4  # how far along the time axis to trace


def spring_shape(start, end, coils=12, width=0.32):
    """Return a zigzag VMobject that looks like a spring between two points."""
    start = np.array(start, dtype=float)
    end = np.array(end, dtype=float)
    span = end - start
    length = np.linalg.norm(span)
    if length < 1e-6:
        return VMobject()
    direction = span / length
    normal = np.array([-direction[1], direction[0], 0.0])

    points = [start]
    segments = coils * 2
    seg_len = length / segments
    for i in range(1, segments):
        offset = width if i % 2 == 1 else -width
        points.append(start + direction * seg_len * i + normal * offset)
    points.append(end)

    spring = VMobject(color=GREY_B, stroke_width=4)
    spring.set_points_as_corners(points)
    return spring


class GeneratedScene(Scene):
    def construct(self):
        title = Text("Simple Harmonic Motion", font_size=40).to_edge(UP)
        self.play(Write(title))

        # A clock that drives all the motion.
        t = ValueTracker(0.0)

        def mass_center_x():
            return EQUILIBRIUM_X + AMPLITUDE * np.cos(OMEGA * t.get_value())

        # --- static parts (wall, floor, equilibrium line) ---
        wall = Line([WALL_X, -1.3, 0], [WALL_X, 1.3, 0], color=GREY, stroke_width=6)
        hatching = VGroup(*[
            Line([WALL_X, y, 0], [WALL_X - 0.3, y + 0.3, 0], color=GREY, stroke_width=2)
            for y in np.linspace(-1.3, 1.0, 8)
        ])
        floor = Line([WALL_X, -0.55, 0], [EQUILIBRIUM_X + AMPLITUDE + 1.0, -0.55, 0],
                     color=GREY_D)

        eq_line = DashedLine([EQUILIBRIUM_X, -1.1, 0], [EQUILIBRIUM_X, 1.1, 0],
                             color=YELLOW)
        eq_label = Text("equilibrium", font_size=20, color=YELLOW).next_to(eq_line, DOWN, buff=0.15)

        self.play(Create(wall), Create(hatching), Create(floor))
        self.play(Create(eq_line), FadeIn(eq_label))

        # --- moving parts (spring, mass, restoring-force arrow) ---
        mass = always_redraw(lambda: Square(
            side_length=MASS_HALF * 2, color=BLUE, fill_opacity=0.85
        ).move_to([mass_center_x(), 0, 0]))

        spring = always_redraw(lambda: spring_shape(
            [WALL_X, 0, 0], [mass_center_x() - MASS_HALF, 0, 0]
        ))

        def force_arrow_maker():
            disp = mass_center_x() - EQUILIBRIUM_X
            if abs(disp) < 0.08:
                return VGroup()  # no visible force near equilibrium
            tip = EQUILIBRIUM_X + 0.5 * disp  # points back toward equilibrium
            return Arrow([mass_center_x(), 0.0, 0], [tip, 0.0, 0],
                         color=RED, buff=0, stroke_width=5)

        force_arrow = always_redraw(force_arrow_maker)
        force_label = Text("restoring force", font_size=18, color=RED).to_edge(LEFT).shift(DOWN * 2)

        self.play(Create(spring), Create(mass))
        self.add(force_arrow)
        self.play(FadeIn(force_label))

        # --- position vs time graph on the right ---
        axes = Axes(
            x_range=[0, T_MAX, 2],
            y_range=[-AMPLITUDE - 0.4, AMPLITUDE + 0.4, 1],
            x_length=4.5,
            y_length=2.6,
            tips=False,
            axis_config={"color": WHITE, "stroke_width": 2},
        ).to_edge(RIGHT).shift(DOWN * 0.3)
        graph_title = Text("position vs time", font_size=22).next_to(axes, UP, buff=0.15)

        self.play(Create(axes), FadeIn(graph_title))

        def graph_point():
            x = t.get_value()
            y = AMPLITUDE * np.cos(OMEGA * x)
            return axes.c2p(x, y)

        tracer = TracedPath(graph_point, stroke_color=RED, stroke_width=3)
        moving_dot = always_redraw(lambda: Dot(graph_point(), color=RED))
        self.add(tracer, moving_dot)

        # --- run the oscillation ---
        self.play(t.animate.set_value(T_MAX), run_time=DURATION, rate_func=linear)
        self.wait(1)
