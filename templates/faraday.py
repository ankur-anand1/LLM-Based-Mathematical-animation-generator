"""Hand-written, tested template: Faraday's Law of Electromagnetic Induction.

A bar magnet moves in and out of a coil. The changing magnetic flux induces an
EMF, shown by a galvanometer needle that deflects with the magnet's speed (and
reverses direction as the magnet reverses). 2D, fast, and clear.

Scene named GeneratedScene so it works with src/renderer.py.
"""

from manim import *
import numpy as np

AMP = 3.2          # how far the magnet travels
OMEGA = 1.2        # speed of the back-and-forth motion
DURATION = 9.0


class GeneratedScene(Scene):
    def construct(self):
        title = Text("Faraday's Law: Electromagnetic Induction", font_size=34).to_edge(UP)
        self.play(Write(title))

        t = ValueTracker(0.0)

        def magnet_x():
            return AMP * np.sin(OMEGA * t.get_value())

        def magnet_v():
            return AMP * OMEGA * np.cos(OMEGA * t.get_value())

        # --- Coil at the centre (a stack of ellipses = solenoid) ---
        coil = VGroup(*[
            Ellipse(width=0.45, height=1.6, color=ORANGE, stroke_width=4).shift(RIGHT * 0.2 * i)
            for i in range(-3, 4)
        ]).move_to(ORIGIN + UP * 0.4)
        coil_label = Text("coil", font_size=22).next_to(coil, UP, buff=0.3)
        self.play(Create(coil), FadeIn(coil_label))

        # --- Bar magnet (N red | S blue) that slides through the coil ---
        def make_magnet():
            n = Rectangle(width=0.9, height=0.55, color=RED, fill_opacity=1)
            s = Rectangle(width=0.9, height=0.55, color=BLUE, fill_opacity=1).next_to(n, RIGHT, buff=0)
            n_lbl = Text("N", font_size=22, color=WHITE).move_to(n)
            s_lbl = Text("S", font_size=22, color=WHITE).move_to(s)
            mag = VGroup(n, s, n_lbl, s_lbl)
            mag.move_to([magnet_x(), 0.4, 0])
            return mag
        magnet = always_redraw(make_magnet)
        self.add(magnet)

        # --- Galvanometer (dial + deflecting needle) below ---
        gal_center = np.array([0.0, -2.4, 0.0])
        dial = Arc(radius=0.9, start_angle=PI, angle=-PI, color=WHITE).move_arc_center_to(gal_center)
        box = SurroundingRectangle(VGroup(dial), color=WHITE, buff=0.25)
        gal_label = Text("galvanometer", font_size=20).next_to(box, DOWN, buff=0.2)

        def needle():
            ang = PI / 2 + float(np.clip(magnet_v() * 0.22, -1.3, 1.3))
            tip = gal_center + 0.8 * np.array([np.cos(ang), np.sin(ang), 0])
            return Line(gal_center, tip, color=YELLOW, stroke_width=5)
        needle_m = always_redraw(needle)

        # --- Wires from coil to galvanometer ---
        wire_l = Line(coil.get_bottom() + LEFT * 0.5, box.get_top() + LEFT * 0.5, color=GREY_B)
        wire_r = Line(coil.get_bottom() + RIGHT * 0.5, box.get_top() + RIGHT * 0.5, color=GREY_B)

        self.play(Create(box), Create(dial), Create(wire_l), Create(wire_r), FadeIn(gal_label))
        self.add(needle_m)

        caption = Text("Moving the magnet changes the flux, inducing a current.",
                       font_size=22).to_edge(DOWN)
        self.play(FadeIn(caption))

        # --- Run the motion ---
        self.play(t.animate.set_value(DURATION), run_time=DURATION, rate_func=linear)
        self.wait(0.5)
