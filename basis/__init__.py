"""Reusable, tested Manim building blocks (a.k.a. 'basis codes').

Each block is a small function that adds ONE correct, animated visual to a
scene, using a shared `ctx` dict so the pieces line up and share one clock.
Compose several blocks to build many different animations from a few parts.
"""

from .blocks import (  # noqa: F401
    new_context,
    add_title,
    add_caption,
    add_axes,
    add_oscillator,
    add_pendulum,
    add_projectile,
    add_phasor,
    add_traveling_wave,
    add_traced_graph,
    add_vector,
    run_time,
)
