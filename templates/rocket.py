"""Hand-written, tested template: Rocket Propulsion (2D, fast + clear).

A rocket launches upward while force arrows show Thrust (up), Gravity (down) and
Drag (down). 2D is used deliberately: it renders in seconds and reads more
clearly for students than a slow 3D solid. Motion is driven by a ValueTracker.

Scene named GeneratedScene so it works with src/renderer.py.
"""

from manim import *
import numpy as np

DURATION = 7.0


def make_rocket(color=GREY_B):
    body = RoundedRectangle(width=0.7, height=1.6, corner_radius=0.15,
                            color=color, fill_opacity=1)
    nose = Triangle(color=RED, fill_opacity=1).scale(0.45).next_to(body, UP, buff=0)
    window = Circle(radius=0.16, color=BLUE, fill_opacity=1).move_to(body.get_center() + UP * 0.3)
    left_fin = Polygon([-0.35, -0.6, 0], [-0.7, -1.0, 0], [-0.35, -0.2, 0],
                       color=RED, fill_opacity=1)
    right_fin = Polygon([0.35, -0.6, 0], [0.7, -1.0, 0], [0.35, -0.2, 0],
                        color=RED, fill_opacity=1)
    return VGroup(left_fin, right_fin, body, nose, window)


class GeneratedScene(Scene):
    def construct(self):
        title = Text("Rocket Propulsion", font_size=40).to_edge(UP)
        self.play(Write(title))

        clock = ValueTracker(0.0)

        def height():
            # accelerating launch that levels off near the top
            return -2.5 + min(0.12 * clock.get_value() ** 2, 4.5)

        rocket = make_rocket()
        rocket.add_updater(lambda m: m.move_to([-3.0, height(), 0]))

        # Flickering exhaust flame (cheap in 2D).
        def flame_maker():
            h = 0.6 + 0.25 * abs(np.sin(8 * clock.get_value()))
            flame = Triangle(color=ORANGE, fill_opacity=1).scale(0.4)
            flame.stretch_to_fit_height(h).rotate(PI)
            flame.next_to([-3.0, height(), 0], DOWN, buff=0).shift(UP * 0.1)
            return flame
        flame = always_redraw(flame_maker)

        # Force arrows placed BESIDE the rocket (not over it) for clarity.
        def thrust():
            base = np.array([-4.4, height() - 0.3, 0])     # left of rocket
            return Arrow(base, base + UP * 1.6, color=GREEN, buff=0)

        def gravity():
            c = np.array([-1.6, height() + 0.4, 0])         # right of rocket
            return Arrow(c, c + DOWN * 1.1, color=RED, buff=0)

        def drag():
            top = np.array([-1.6, height() + 1.4, 0])       # right, above gravity
            return Arrow(top, top + DOWN * 0.6, color=ORANGE, buff=0)

        thrust_arrow = always_redraw(thrust)
        gravity_arrow = always_redraw(gravity)
        drag_arrow = always_redraw(drag)

        # Static legend on the right.
        legend = VGroup(
            Text("Thrust", font_size=24, color=GREEN),
            Text("Gravity", font_size=24, color=RED),
            Text("Drag", font_size=24, color=ORANGE),
        ).arrange(DOWN, buff=0.4, aligned_edge=LEFT).to_edge(RIGHT).shift(UP * 0.5)

        self.add(rocket, flame, thrust_arrow, gravity_arrow, drag_arrow)
        self.play(FadeIn(legend))
        self.play(clock.animate.set_value(DURATION), run_time=DURATION, rate_func=linear)
        rocket.clear_updaters()
        self.wait(0.5)
