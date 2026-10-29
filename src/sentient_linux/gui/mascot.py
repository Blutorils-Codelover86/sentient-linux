"""
Official Sentient OS Mascot with MACL Living Intelligence.
Faithfully renders the upstream Sentient mark using Cairo, with state-reactive living animations.
"""

from __future__ import annotations
import math
import time
from enum import Enum
from typing import List, Tuple

import cairo
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, GLib

from sentient_linux.gui.theme import THEME, ColorRGB


class MascotState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ACTING = "acting"
    AWAITING_APPROVAL = "awaiting_approval"
    ERROR = "error"


class LivingMascot(Gtk.DrawingArea):
    """
    Cairo-rendered procedural Sentient mark with living intelligence motion.
    Features:
    - Saturated AI-spectrum ring (SpinningLogo.bandStops).
    - Glowing white planet core and heart.
    - Keplerian particle motes with 5.5s harmonic breath.
    - Stateful transitions: Idle, Listening, Thinking, Acting, Awaiting Approval, Error.
    - Low-power and reduced-motion modes.
    """

    def __init__(self, size: int = 28, low_power: bool = False, reduced_motion: bool = False) -> None:
        super().__init__()
        self.size = size
        self.low_power = low_power
        self.reduced_motion = reduced_motion

        self.set_content_width(size)
        self.set_content_height(size)
        self.set_draw_func(self._on_draw)

        self._state = MascotState.IDLE
        self._start_time = time.perf_counter()
        self._error_timestamp: float = 0.0

        # Seed fixed particle motes for deterministic constellation reproduction
        self._particles = self._generate_particles(count=12)

        # 30 FPS tick for silky living motion without high CPU consumption
        interval_ms = 66 if low_power else 33
        if not self.reduced_motion:
            GLib.timeout_add(interval_ms, self._on_tick)

    def _generate_particles(self, count: int) -> List[Tuple[float, float, float, float]]:
        """Generate static orbital particles: (radius_factor, initial_angle, speed_mult, size_factor)."""
        particles = []
        for i in range(count):
            angle = (i / count) * 2 * math.pi
            r_factor = 0.82 + 0.16 * math.sin(i * 1.7)
            speed = 1.0 + 0.4 * math.cos(i * 2.3)
            s_factor = 0.05 + 0.03 * math.sin(i * 3.1)
            particles.append((r_factor, angle, speed, s_factor))
        return particles

    @property
    def state(self) -> MascotState:
        return self._state

    @state.setter
    def state(self, new_state: MascotState) -> None:
        if new_state != self._state:
            self._state = new_state
            if new_state == MascotState.ERROR:
                self._error_timestamp = time.perf_counter()
            self.queue_draw()

    def set_reduced_motion(self, enabled: bool) -> None:
        self.reduced_motion = enabled
        self.queue_draw()

    def set_low_power(self, enabled: bool) -> None:
        self.low_power = enabled
        self.queue_draw()

    def _on_tick(self) -> bool:
        if not self.reduced_motion:
            self.queue_draw()
        return True

    def _interpolate_color(self, stops: Tuple[ColorRGB, ...], frac: float) -> Tuple[float, float, float]:
        f = frac % 1.0
        n = len(stops) - 1
        pos = f * n
        idx = int(pos)
        rem = pos - idx
        c1 = stops[idx]
        c2 = stops[idx + 1] if idx + 1 < len(stops) else stops[0]
        r = c1[0] + (c2[0] - c1[0]) * rem
        g = c1[1] + (c2[1] - c1[1]) * rem
        b = c1[2] + (c2[2] - c1[2]) * rem
        return (r, g, b)

    def _on_draw(self, area: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
        now = time.perf_counter()
        elapsed = now - self._start_time

        # Calculate rotation rate by state
        period = 13.0  # seconds per rev (idle)
        if self._state == MascotState.THINKING:
            period = 2.0   # fast processing spin
        elif self._state == MascotState.ACTING:
            period = 1.5   # active execution
        elif self._state == MascotState.LISTENING:
            period = 8.0   # attentive drift

        if self.reduced_motion:
            angle = 0.0
            breath = 0.5
        else:
            angle = (elapsed / period) * 2 * math.pi
            # 5.5-second harmonic breath cycle
            breath = (math.sin(elapsed * 2 * math.pi / 5.5) + 1.0) / 2.0

        cx = width / 2.0
        cy = height / 2.0
        s = min(width, height)

        # 1. Outer Soft Ambient Bloom
        bloom_radius = (s * 0.44) * (1.0 + 0.04 * breath)
        bloom_pat = cairo.RadialGradient(cx, cy, s * 0.15, cx, cy, bloom_radius)
        if self._state == MascotState.AWAITING_APPROVAL:
            # Warm amber glow
            bloom_pat.add_color_stop_rgba(0.0, THEME.amber[0], THEME.amber[1], THEME.amber[2], 0.35)
        elif self._state == MascotState.ERROR:
            # Soft red disturbance
            bloom_pat.add_color_stop_rgba(0.0, THEME.red[0], THEME.red[1], THEME.red[2], 0.45)
        else:
            # Subtle violet/spectrum ambient bloom
            bloom_pat.add_color_stop_rgba(0.0, THEME.accent[0], THEME.accent[1], THEME.accent[2], 0.28)
        bloom_pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)

        cr.set_source(bloom_pat)
        cr.arc(cx, cy, bloom_radius, 0, 2 * math.pi)
        cr.fill()

        # 2. Thick Saturated Spectrum Ring
        ring_radius = (s * 0.38) * (1.0 + 0.02 * breath)
        ring_width = max(2.0, s * 0.16)
        segments = 36
        for i in range(segments):
            seg_start = angle + (i / segments) * 2 * math.pi
            seg_end = seg_start + (2 * math.pi / segments) + 0.03

            color_frac = (i / segments)
            if self._state == MascotState.AWAITING_APPROVAL:
                # Tint towards warm amber
                r, g, b = THEME.amber
            elif self._state == MascotState.ERROR and (now - self._error_timestamp < 1.5):
                # Temporary red flash
                r, g, b = THEME.red
            else:
                r, g, b = self._interpolate_color(THEME.mascot_stops, color_frac)

            cr.set_source_rgb(r, g, b)
            cr.set_line_width(ring_width)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.arc(cx, cy, ring_radius, seg_start, seg_end)
            cr.stroke()

        # 3. Orbiting Constellation Motes (Living Particles)
        if not self.reduced_motion:
            for r_factor, a0, speed_mult, s_factor in self._particles:
                p_angle = a0 + (elapsed * speed_mult * 0.8)
                p_r = ring_radius * r_factor
                px = cx + p_r * math.cos(p_angle)
                py = cy + p_r * math.sin(p_angle)
                p_size = max(1.0, s * s_factor)

                cr.set_source_rgba(1.0, 1.0, 1.0, 0.75 + 0.25 * math.sin(elapsed * 3 + a0))
                cr.arc(px, py, p_size, 0, 2 * math.pi)
                cr.fill()

        # 4. Razor-Thin White Shape Ring
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.85)
        cr.set_line_width(max(0.75, s * 0.028))
        cr.arc(cx, cy, ring_radius - ring_width / 2.0, 0, 2 * math.pi)
        cr.stroke()

        # 5. Core Additive Lit Heart (Glowing White)
        heart_radius = (s * 0.22) * (1.0 + 0.06 * breath)
        if self._state == MascotState.LISTENING:
            heart_radius *= 1.15  # Expand during listening

        heart_pat = cairo.RadialGradient(cx, cy, 0, cx, cy, heart_radius)
        heart_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.65)
        heart_pat.add_color_stop_rgba(0.7, 1.0, 1.0, 1.0, 0.25)
        heart_pat.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(heart_pat)
        cr.arc(cx, cy, heart_radius, 0, 2 * math.pi)
        cr.fill()

        # 6. Central Brilliant White Planet Core Dot
        core_radius = s * 0.16
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.arc(cx, cy, core_radius, 0, 2 * math.pi)
        cr.fill()
