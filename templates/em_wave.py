"""Hand-written, tested 3D template: Electromagnetic Wave.

A real 3D scene (ThreeDScene) with a rotating camera. The electric field (E)
oscillates in the vertical plane and the magnetic field (B) oscillates in the
horizontal plane, perpendicular to each other, both propagating along x. This
is the classic "solid 3D" physics visual that helps students see the structure.

Scene named GeneratedScene so it works with src/renderer.py.
"""

from manim import *
import numpy as np

AMP = 1.5
K = 1.0            # spatial frequency
W = 2.0            # angular frequency
X_MIN, X_MAX = -5.0, 5.0
DURATION = 8.0


class GeneratedScene(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(
            x_range=[X_MIN, X_MAX, 1], y_range=[-2, 2, 1], z_range=[-2, 2, 1],
            x_length=10, y_length=4, z_length=4,
        )

        # 2D overlay title (stays facing the camera).
        title = Text("Electromagnetic Wave (3D)", font_size=36)
        self.add_fixed_in_frame_mobjects(title)
        title.to_edge(UP)

        e_label = Text("E field", font_size=24, color=YELLOW)
        b_label = Text("B field", font_size=24, color=BLUE)
        self.add_fixed_in_frame_mobjects(e_label, b_label)
        e_label.to_corner(UL).shift(DOWN * 0.8)
        b_label.next_to(e_label, DOWN, buff=0.2)

        self.set_camera_orientation(phi=70 * DEGREES, theta=-50 * DEGREES)
        self.play(Create(axes))

        t = ValueTracker(0.0)

        # E field: oscillates in z (vertical), along x.
        e_wave = always_redraw(lambda: ParametricFunction(
            lambda x: axes.c2p(x, 0, AMP * np.sin(K * x - W * t.get_value())),
            t_range=[X_MIN, X_MAX, 0.1], color=YELLOW,
        ))
        # B field: oscillates in y (horizontal), along x.
        b_wave = always_redraw(lambda: ParametricFunction(
            lambda x: axes.c2p(x, AMP * np.sin(K * x - W * t.get_value()), 0),
            t_range=[X_MIN, X_MAX, 0.1], color=BLUE,
        ))

        # A few field "sticks" so the perpendicular structure is clear.
        sample_xs = np.linspace(X_MIN + 0.5, X_MAX - 0.5, 9)

        def e_sticks():
            grp = VGroup()
            for x in sample_xs:
                z = AMP * np.sin(K * x - W * t.get_value())
                grp.add(Line(axes.c2p(x, 0, 0), axes.c2p(x, 0, z), color=YELLOW, stroke_width=3))
            return grp

        def b_sticks():
            grp = VGroup()
            for x in sample_xs:
                y = AMP * np.sin(K * x - W * t.get_value())
                grp.add(Line(axes.c2p(x, 0, 0), axes.c2p(x, y, 0), color=BLUE, stroke_width=3))
            return grp

        e_field = always_redraw(e_sticks)
        b_field = always_redraw(b_sticks)

        prop = Arrow3D(axes.c2p(X_MIN, 0, 0), axes.c2p(X_MAX, 0, 0), color=GREEN)

        self.add(e_wave, b_wave, e_field, b_field, prop)
        self.begin_ambient_camera_rotation(rate=0.15)
        self.play(t.animate.set_value(W * DURATION), run_time=DURATION, rate_func=linear)
        self.stop_ambient_camera_rotation()
        self.wait(0.5)
