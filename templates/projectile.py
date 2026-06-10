"""Hand-written, tested template: Projectile Motion.

A ball is launched at an angle, follows a parabolic path under gravity, traces
its trajectory, and shows its velocity vector (tangent to the path). The motion
is driven by a ValueTracker clock, so it is always physically correct.

The Scene is named GeneratedScene so it works with src/renderer.py.
"""

from manim import *
import numpy as np

# --- physics parameters ---
G = 9.8
V0 = 7.0                 # launch speed
ANGLE_DEG = 60.0         # launch angle
VX = V0 * np.cos(np.radians(ANGLE_DEG))
VY = V0 * np.sin(np.radians(ANGLE_DEG))
FLIGHT_TIME = 2 * VY / G
RANGE = VX * FLIGHT_TIME
MAX_HEIGHT = VY * VY / (2 * G)


class GeneratedScene(Scene):
    def construct(self):
        title = Text("Projectile Motion", font_size=40).to_edge(UP)
        self.play(Write(title))

        # Axes sized to fit the whole flight, placed lower on screen.
        axes = Axes(
            x_range=[0, RANGE * 1.1, 1],
            y_range=[0, MAX_HEIGHT * 1.3, 1],
            x_length=10,
            y_length=4.2,
            tips=False,
            axis_config={"color": GREY_B, "stroke_width": 2},
        ).to_edge(DOWN, buff=0.8)

        x_label = Text("horizontal distance", font_size=20).next_to(axes.x_axis, DOWN, buff=0.2)
        y_label = Text("height", font_size=20).next_to(axes.y_axis, LEFT, buff=0.1).rotate(PI / 2)

        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label))

        # The clock that drives the motion.
        t = ValueTracker(0.0)

        def pos(time):
            x = VX * time
            y = VY * time - 0.5 * G * time * time
            return x, y

        def ball_point():
            x, y = pos(t.get_value())
            return axes.c2p(x, max(y, 0))

        ball = always_redraw(lambda: Dot(ball_point(), color=BLUE, radius=0.12))

        # Trajectory traced as the ball flies.
        trajectory = TracedPath(ball_point, stroke_color=YELLOW, stroke_width=3)

        # Velocity vector (tangent to the path), scaled down to look reasonable.
        def velocity_arrow():
            time = t.get_value()
            vx, vy = VX, VY - G * time
            x, y = pos(time)
            start = axes.c2p(x, max(y, 0))
            end = axes.c2p(x + vx * 0.18, max(y, 0) + vy * 0.18)
            return Arrow(start, end, color=RED, buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.25)

        v_arrow = always_redraw(velocity_arrow)
        v_label = Text("velocity", font_size=18, color=RED).to_edge(RIGHT).shift(UP * 2)

        self.add(trajectory, ball, v_arrow)
        self.play(FadeIn(v_label))

        # Run the flight.
        self.play(t.animate.set_value(FLIGHT_TIME), run_time=6, rate_func=linear)
        self.wait(1)
