"""
Official Sentient OS Mascot with MACL Living Intelligence.
Faithfully renders the upstream Sentient mark using Cairo, with state-reactive living animations.
Ported from SpinningLogo.swift, Orb.swift, and SidekickStyle.swift.
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
    Faithful port of upstream SpinningLogo.swift:
    - Saturated AI-spectrum ring (SpinningLogo.bandStops with saturated gold seam).
    - Glowing white planet core and heart.
    - Continuous wall-clock phase anchoring across speed changes.
    - 5.5s harmonic breathing cycle.
    - Low-power (30 FPS) and reduced-motion modes.
    """

    def __init__(self, size: int = 24, low_power: bool = False, reduced_motion: bool = False) -> None:
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

        # Anchor angle & time for seamless speed switching without rotational jumps
        self._anchor_angle: float = 0.0
        self._anchor_time: float = self._start_time
        self._current_period: float = 13.0

        # Seed fixed particle motes for deterministic constellation reproduction
        self._particles = self._generate_particles(count=12)

        # 30 FPS tick for silky living motion with negligible CPU consumption
        interval_ms = 66 if low_power else 33
        if not self.reduced_motion:
            GLib.timeout_add(interval_ms, self._on_tick)

    def _generate_particles(self, count: int) -> List[Tuple[float, float, float, float]]:
        """Generate static orbital particles: (radius_factor, initial_angle, speed_mult, size_factor)."""
        particles = []
        for i in range(count):
            angle = (i / count) * 2 * math.pi
            r_factor = 0.85 + 0.15 * math.sin(i * 1.7)
            speed = 1.0 + 0.3 * math.cos(i * 2.3)
            s_factor = 0.045 + 0.025 * math.sin(i * 3.1)
            particles.append((r_factor, angle, speed, s_factor))
        return particles

    @property
    def state(self) -> MascotState:
        return self._state

    @state.setter
    def state(self, new_state: MascotState) -> None:
        if new_state != self._state:
            now = time.perf_counter()
            old_period = self._get_period(self._state)
            new_period = self._get_period(new_state)

            # Re-base rotation phase so speed change never jumps or rewinds
            if not self.reduced_motion:
                elapsed_since_anchor = now - self._anchor_time
                self._anchor_angle = (self._anchor_angle + (elapsed_since_anchor / old_period) * 2 * math.pi) % (2 * math.pi)
                self._anchor_time = now

            self._state = new_state
            self._current_period = new_period
            if new_state == MascotState.ERROR:
                self._error_timestamp = now
            self.queue_draw()

    def _get_period(self, state: MascotState) -> float:
        """Upstream SpinningLogo.swift: 2s fast processing, 13s idle spin."""
        if state in (MascotState.THINKING, MascotState.ACTING):
            return 2.0
        elif state == MascotState.LISTENING:
            return 6.0
        return 13.0

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
        elapsed_total = now - self._start_time

        if self.reduced_motion:
            angle = 0.0
            breath = 0.5
        else:
            # Anchored rotation angle
            elapsed_anchor = now - self._anchor_time
            angle = (self._anchor_angle + (elapsed_anchor / self._current_period) * 2 * math.pi) % (2 * math.pi)
            # 5.5s harmonic heartbeat breathing from Orb.swift
            breath = (math.sin(elapsed_total * 2 * math.pi / 5.5) + 1.0) / 2.0

        cx = width / 2.0
        cy = height / 2.0
        s = min(width, height)

        # 1. Outer Soft Colored Neon Bloom (additive bleed)
        bloom_radius = (s * 0.44) * (1.0 + 0.04 * breath)
        bloom_pat = cairo.RadialGradient(cx, cy, s * 0.15, cx, cy, bloom_radius)
        if self._state == MascotState.AWAITING_APPROVAL:
            bloom_pat.add_color_stop_rgba(0.0, THEME.amber[0], THEME.amber[1], THEME.amber[2], 0.35)
        elif self._state == MascotState.ERROR:
            bloom_pat.add_color_stop_rgba(0.0, THEME.red[0], THEME.red[1], THEME.red[2], 0.45)
        else:
            # Soft violet/spectrum bloom
            bloom_pat.add_color_stop_rgba(0.0, THEME.accent[0], THEME.accent[1], THEME.accent[2], 0.28)
        bloom_pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)

        cr.set_source(bloom_pat)
        cr.arc(cx, cy, bloom_radius, 0, 2 * math.pi)
        cr.fill()

        # 2. Saturated Spectrum Color Band (SpinningLogo: lineWidth = size * 0.17)
        ring_radius = (s * 0.38) * (1.0 + 0.02 * breath)
        ring_width = max(2.0, s * 0.17)
        segments = 36
        for i in range(segments):
            seg_start = angle + (i / segments) * 2 * math.pi
            seg_end = seg_start + (2 * math.pi / segments) + 0.03

            color_frac = (i / segments)
            if self._state == MascotState.AWAITING_APPROVAL:
                r, g, b = THEME.amber
            elif self._state == MascotState.ERROR and (now - self._error_timestamp < 1.5):
                r, g, b = THEME.red
            else:
                r, g, b = self._interpolate_color(THEME.mascot_stops, color_frac)

            cr.set_source_rgb(r, g, b)
            cr.set_line_width(ring_width)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.arc(cx, cy, ring_radius, seg_start, seg_end)
            cr.stroke()

        # 3. Living Constellation Motes (Living Intelligence enhancement)
        if not self.reduced_motion:
            for r_factor, a0, speed_mult, s_factor in self._particles:
                p_angle = a0 + (elapsed_total * speed_mult * 0.8)
                p_r = ring_radius * r_factor
                px = cx + p_r * math.cos(p_angle)
                py = cy + p_r * math.sin(p_angle)
                p_size = max(1.0, s * s_factor)

                cr.set_source_rgba(1.0, 1.0, 1.0, 0.70 + 0.30 * math.sin(elapsed_total * 3 + a0))
                cr.arc(px, py, p_size, 0, 2 * math.pi)
                cr.fill()

        # 4. Razor-Thin White Shape Ring (SpinningLogo: max(0.75, size * 0.028))
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.90)
        cr.set_line_width(max(0.75, s * 0.028))
        cr.arc(cx, cy, ring_radius - ring_width / 2.0, 0, 2 * math.pi)
        cr.stroke()

        # 5. Core Additive Lit Heart (SpinningLogo: width = size * 0.50, opacity 0.6)
        heart_radius = (s * 0.25) * (1.0 + 0.05 * breath)
        if self._state == MascotState.LISTENING:
            heart_radius *= 1.15

        heart_pat = cairo.RadialGradient(cx, cy, 0, cx, cy, heart_radius)
        heart_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.65)
        heart_pat.add_color_stop_rgba(0.7, 1.0, 1.0, 1.0, 0.25)
        heart_pat.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(heart_pat)
        cr.arc(cx, cy, heart_radius, 0, 2 * math.pi)
        cr.fill()

        # 6. Central Brilliant White Planet Core Dot (SpinningLogo: width = size * 0.36)
        core_radius = s * 0.18
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.arc(cx, cy, core_radius, 0, 2 * math.pi)
        cr.fill()


class SidekickMark(Gtk.DrawingArea):
    """
    Upstream SidekickMark parity widget (from SidekickStyle.swift):
    Draws static or illuminated OrbMark with an ambient angular-gradient halo.
    Used prominently in the transcript empty state.
    """

    def __init__(self, size: int = 32, illuminated: bool = True) -> None:
        super().__init__()
        self.size = size
        self.illuminated = illuminated
        self.set_content_width(size + (16 if illuminated else 0))
        self.set_content_height(size + (16 if illuminated else 0))
        self.set_draw_func(self._on_draw)

    def _on_draw(self, area: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
        cx = width / 2.0
        cy = height / 2.0
        s = float(self.size)

        # Ambient illuminated halo if requested
        if self.illuminated:
            halo_radius = s * 0.65
            halo_pat = cairo.RadialGradient(cx, cy, s * 0.2, cx, cy, halo_radius)
            halo_pat.add_color_stop_rgba(0.0, 0.69, 0.42, 0.70, 0.48)
            halo_pat.add_color_stop_rgba(0.6, 0.99, 0.88, 0.64, 0.28)
            halo_pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
            cr.set_source(halo_pat)
            cr.arc(cx, cy, halo_radius, 0, 2 * math.pi)
            cr.fill()

        # OrbMark: Outer circle stroke
        line_width = max(1.0, s * 0.085)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.92)
        cr.set_line_width(line_width)
        cr.arc(cx, cy, (s / 2.0) - (line_width / 2.0), 0, 2 * math.pi)
        cr.stroke()

        # OrbMark: Central planet dot (width: size * 0.38)
        dot_radius = (s * 0.38) / 2.0
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.arc(cx, cy, dot_radius, 0, 2 * math.pi)
        cr.fill()
