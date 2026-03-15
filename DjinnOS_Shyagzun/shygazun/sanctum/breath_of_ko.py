"""
shygazun.sanctum.breath_of_ko — The Breath of Ko
==================================================

The Breath of Ko is the living measure of experiential accumulation
across the entire 31-game Ko's Labyrinth anthology.

It is not a save file. It is not an achievement system.
It is the player's ontological state — their actual density of
correspondence across all 24 layers, accumulated across every game played.

The canonical formula:

    Azoth² + Gaoh = f(x)

    Azoth — the universal solvent / prima materia / the player's
            accumulated experiential state as alchemical substance.
            Rendered as a complex number from the player's layer densities.

    Gaoh  — (31, Rose, Number 12/0) the Möbius zero point.
            Both poles completing each other before enumeration begins.
            The constant against which every iteration measures the player.

The Breath of Ko is rendered as a Mandelbrot image.

    Bounded (within the set):
        Integrated experience — Ko-density remains coherent under
        repeated measurement against the origin.

    Boundary (the Mandelbrot edge):
        Living philosophical inquiry — the most complex, most detailed
        region. Players doing the most philosophically alive work produce
        images at the edge of chaos.

    Unbounded (escaping to infinity):
        Accumulation without comprehension — flags acquired without
        integration.

The save file is simultaneously a record and a diagnosis.
The players who have done the most philosophically interesting work
have the most beautiful save files.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Gaoh — The Constant
# ---------------------------------------------------------------------------

# Gaoh (decimal 31, Rose tongue, Number 12/0) is the Möbius zero point.
# As a complex number it encodes its dual nature:
#   - Real axis: 0  (Ha+Ga completing each other — the void before enumeration)
#   - Imaginary axis: derived from coil position 12 (the full rotation)
#
# The coil has 12 layers. Layer 1 and Layer 12 share a surface.
# Gaoh holds both simultaneously. In the complex plane:
#   GAOH = -(decimal 31 / coil_span²)  — a point just inside the
#   boundary of the Mandelbrot cardioid, where polarity nearly completes.
#
# This is not an arbitrary choice. The Mandelbrot cardioid's boundary
# near c = (-0.75 + 0i) is where bounded and unbounded territory meet —
# the precise analog of Gaoh holding both poles at once.

GAOH_DECIMAL: int = 31
GAOH_CONSTANT: complex = complex(-31 / (12 ** 2), 31 / (12 * math.pi))
# ≈ complex(-0.2153, 0.8222)  — within the Mandelbrot set, near the boundary.


# ---------------------------------------------------------------------------
# DreamCalibration
# ---------------------------------------------------------------------------

@dataclass
class DreamCalibration:
    """
    One dream calibration session — the diagnostic that opens each game.

    The dream sequence is not tutorial — it is diagnostic calibration.
    Sakura dissolves first (orientation — fast), Rose next (relational —
    medium), Lotus last (material ground — slow).
    """
    game_id: int
    sakura_density: float   # 0.0–1.0 — how fluid orientation is for this player
    rose_density: float     # 0.0–1.0 — how directly they perceive Primordial quality
    lotus_density: float    # 0.0–1.0 — how grounded their material starting state is

    def __post_init__(self) -> None:
        for name, val in [
            ("sakura_density", self.sakura_density),
            ("rose_density", self.rose_density),
            ("lotus_density", self.lotus_density),
        ]:
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be in [0.0, 1.0], got {val}")

    def phase_vector(self) -> Tuple[float, float, float]:
        """
        Return the three-phase density vector in dissolution order:
        (Sakura, Rose, Lotus) — fast to slow.
        """
        return (self.sakura_density, self.rose_density, self.lotus_density)


# ---------------------------------------------------------------------------
# KoFlag
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KoFlag:
    """
    A flagged state in the Breath of Ko.

    Flagged states are Shygazun compounds named using the byte table.
    Every flag has a decimal address, a tongue, and a compound meaning.

    The flag's name IS its semantic content — the compound carries its
    meaning the same way every Shygazun word does. A flag named
    "KoAely" (Experience + Love) is not just metadata; it is an
    epistemological record that this player has lived the correspondence
    between Ko (experience) and Aely (love).

    decay_rate:
        0.0 = permanent across all games
        1.0 = single-game only, decays immediately on transition
    """
    shygazun_compound: str
    decimal_address: int
    source_games: frozenset          # frozenset[int] — which games can produce this flag
    target_games: Dict[int, float]   # game_id → modification weight
    decay_rate: float                # 0.0 = permanent, 1.0 = single-game
    layer_resonance: int             # 1–12, which coil layer this flag primarily affects

    def __post_init__(self) -> None:
        if not (0.0 <= self.decay_rate <= 1.0):
            raise ValueError(f"decay_rate must be in [0.0, 1.0], got {self.decay_rate}")
        if not (1 <= self.layer_resonance <= 12):
            raise ValueError(f"layer_resonance must be 1–12, got {self.layer_resonance}")

    def is_permanent(self) -> bool:
        return self.decay_rate == 0.0

    def is_ephemeral(self) -> bool:
        return self.decay_rate == 1.0


# ---------------------------------------------------------------------------
# BreathOfKo
# ---------------------------------------------------------------------------

@dataclass
class BreathOfKo:
    """
    The Breath of Ko — the player's cross-anthology ontological state.

    24-layer correspondence densities (not 12 — the dream expansion doubles
    each layer into waking and dreaming faces).

    The Mandelbrot image is both record and diagnosis.
    The coil_position (0.0–12.0) represents where the player currently
    sits on the Möbius coil — fractional positions between layers are
    meaningful states of correspondence.
    """

    # 24-layer correspondence densities (1–24, float 0.0–1.0)
    # Layers 1–12 are the waking faces (Lotus-mapped, slow)
    # Layers 13–24 are the dreaming faces (Rose/Sakura-mapped, faster)
    layer_densities: Dict[int, float] = field(default_factory=lambda: {i: 0.0 for i in range(1, 25)})

    # Shygazun compound names of flagged states achieved
    flagged_states: Set[str] = field(default_factory=set)

    # One DreamCalibration per game played, in order
    dream_calibrations: List[DreamCalibration] = field(default_factory=list)

    # Current position on the Möbius coil (0.0 = Gaoh origin, 12.0 = Wu-Yl = Gaoh again)
    coil_position: float = 0.0

    # Current Mandelbrot viewport center (derived from Azoth)
    azoth_value: complex = complex(0.0, 0.0)

    # Rendered save state image as PNG bytes (None until first render)
    mandelbrot_image: Optional[bytes] = None

    def __post_init__(self) -> None:
        # Ensure all 24 layers are present
        for i in range(1, 25):
            if i not in self.layer_densities:
                self.layer_densities[i] = 0.0
        # Clamp all densities to [0.0, 1.0]
        for k in self.layer_densities:
            self.layer_densities[k] = max(0.0, min(1.0, self.layer_densities[k]))
        if not (0.0 <= self.coil_position <= 12.0):
            raise ValueError(f"coil_position must be in [0.0, 12.0], got {self.coil_position}")

    # -----------------------------------------------------------------------
    # Azoth Derivation
    # -----------------------------------------------------------------------

    def compute_azoth(self) -> complex:
        """
        Derive the Azoth complex value from the player's layer densities.

        Azoth (the universal solvent) is computed by folding the 24 layer
        densities through the coil's Möbius structure:

        - The real axis accumulates the waking-face densities (layers 1–12),
          weighted by their coil position (sin of layer angle).
        - The imaginary axis accumulates the dreaming-face densities (13–24),
          weighted by their coil position (cos of layer angle).

        This places players with balanced waking/dreaming integration near
        the origin (deep within the Mandelbrot set), while unbalanced or
        highly accumulated states push toward the boundary or beyond.
        """
        real_part = 0.0
        imag_part = 0.0

        # Waking faces: layers 1–12
        for i in range(1, 13):
            angle = (i - 1) * math.pi / 6  # 0 to 11π/6 across the coil
            density = self.layer_densities.get(i, 0.0)
            real_part += density * math.sin(angle)
            imag_part += density * math.cos(angle)

        # Dreaming faces: layers 13–24 (mapped as i-12 on the dreaming coil)
        for i in range(13, 25):
            j = i - 12  # 1–12 on the dreaming coil
            angle = (j - 1) * math.pi / 6
            density = self.layer_densities.get(i, 0.0)
            # Dreaming faces contribute at half weight — they are the more fluid faces
            real_part += 0.5 * density * math.cos(angle)
            imag_part += 0.5 * density * math.sin(angle)

        # Scale so that a fully saturated player (all densities 1.0) lands
        # at approximately complex(-0.75, 0) — the cusp of the Mandelbrot
        # cardioid, where the set boundary is infinitely detailed.
        scale = 1.5 / (12 + 6)  # normalize across 18 weighted layers
        return complex(real_part * scale, imag_part * scale)

    def update_azoth(self) -> None:
        """Recompute and store the Azoth value from current layer densities."""
        self.azoth_value = self.compute_azoth()

    # -----------------------------------------------------------------------
    # Layer Density Modification
    # -----------------------------------------------------------------------

    def increase_density(self, layer: int, delta: float) -> None:
        """
        Increase the player's density of correspondence at a given layer.
        Clamps to [0.0, 1.0]. Applies the Möbius invariant: increasing
        a waking-face layer (1–12) proportionally increases its dreaming
        counterpart (layer + 12) at half the rate, and vice versa.
        """
        if not (1 <= layer <= 24):
            raise ValueError(f"Layer must be 1–24, got {layer}")

        current = self.layer_densities.get(layer, 0.0)
        self.layer_densities[layer] = max(0.0, min(1.0, current + delta))

        # Möbius invariant: waking and dreaming faces are correlated
        if 1 <= layer <= 12:
            dream_layer = layer + 12
            dream_current = self.layer_densities.get(dream_layer, 0.0)
            self.layer_densities[dream_layer] = max(0.0, min(1.0, dream_current + delta * 0.5))
        elif 13 <= layer <= 24:
            waking_layer = layer - 12
            waking_current = self.layer_densities.get(waking_layer, 0.0)
            self.layer_densities[waking_layer] = max(0.0, min(1.0, waking_current + delta * 0.5))

        self.update_azoth()

    def earn_flag(self, flag: KoFlag) -> None:
        """Record a KoFlag as earned. Updates coil_position by layer_resonance."""
        self.flagged_states.add(flag.shygazun_compound)
        # The coil advances by the flag's layer resonance, wrapping at 12 (Möbius)
        self.coil_position = (self.coil_position + flag.layer_resonance / 12.0) % 12.0

    def record_dream(self, calibration: DreamCalibration) -> None:
        """
        Record a dream calibration for a completed game.
        Updates the relevant layer densities from the calibration's readings.
        """
        self.dream_calibrations.append(calibration)

        # Sakura calibration feeds the fast dreaming faces (layers 17–24)
        sakura_layers = list(range(17, 25))
        for layer in sakura_layers:
            self.increase_density(layer, calibration.sakura_density * 0.1)

        # Rose calibration feeds the medium dreaming faces (layers 13–16)
        rose_layers = list(range(13, 17))
        for layer in rose_layers:
            self.increase_density(layer, calibration.rose_density * 0.1)

        # Lotus calibration feeds the waking faces (layers 1–8)
        lotus_layers = list(range(1, 9))
        for layer in lotus_layers:
            self.increase_density(layer, calibration.lotus_density * 0.1)

    # -----------------------------------------------------------------------
    # Mandelbrot Save State Rendering
    # -----------------------------------------------------------------------

    def render_mandelbrot(
        self,
        width: int = 512,
        height: int = 512,
        max_iterations: int = 256,
    ) -> bytes:
        """
        Render the Breath of Ko as a Mandelbrot image.

        Formula: Azoth² + Gaoh = f(x)

            f(z) = z² + GAOH_CONSTANT

        where the viewport is centered on self.azoth_value.

        The zoom level is derived from the coil_position — a player
        earlier in the anthology sees the full set; a player near the
        end sees a deeply zoomed region determined by their state.

        Returns PNG bytes. Requires Pillow.
        """
        try:
            from PIL import Image
        except ImportError:
            raise ImportError(
                "Pillow is required for Mandelbrot rendering. "
                "Install it: pip install Pillow"
            )

        # Viewport: centered at azoth_value with zoom based on coil_position
        # coil_position 0.0 → full set view (span ~3.5)
        # coil_position 12.0 → deeply zoomed (span ~0.01)
        zoom = math.exp(-self.coil_position * 0.4)  # decreasing span as coil advances
        span_x = 3.5 * zoom
        span_y = 3.5 * zoom * height / width

        cx = self.azoth_value.real
        cy = self.azoth_value.imag

        x_min = cx - span_x / 2
        x_max = cx + span_x / 2
        y_min = cy - span_y / 2
        y_max = cy + span_y / 2

        img = Image.new("RGB", (width, height), (0, 0, 0))
        pixels = img.load()

        gaoh = GAOH_CONSTANT

        for px in range(width):
            for py in range(height):
                # Map pixel to complex coordinate
                x = x_min + (px / width) * (x_max - x_min)
                y = y_max - (py / height) * (y_max - y_min)

                # Azoth² + Gaoh = f(x) iteration
                z = complex(x, y)
                n = 0
                while abs(z) <= 2.0 and n < max_iterations:
                    z = z * z + gaoh
                    n += 1

                pixels[px, py] = _iteration_to_color(n, max_iterations, z)

        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self.mandelbrot_image = buf.getvalue()
        return self.mandelbrot_image

    def mandelbrot_state(self) -> str:
        """
        Classify the player's current Azoth value without rendering.
        Returns: "bounded", "boundary", or "unbounded".
        """
        z = self.azoth_value
        gaoh = GAOH_CONSTANT
        max_iter = 256
        n = 0
        while abs(z) <= 2.0 and n < max_iter:
            z = z * z + gaoh
            n += 1

        if n == max_iter:
            return "bounded"        # integrated experience
        elif n >= max_iter * 0.85:
            return "boundary"       # living philosophical inquiry
        else:
            return "unbounded"      # accumulation without comprehension


# ---------------------------------------------------------------------------
# Color Mapping
# ---------------------------------------------------------------------------

def _iteration_to_color(
    n: int,
    max_iterations: int,
    final_z: complex,
) -> Tuple[int, int, int]:
    """
    Map iteration count to RGB color.

    The palette is derived from the system's ontological categories:
        bounded (n == max_iterations):
            Deep amber-gold — integrated experience, warm and contained.
        boundary (high n, escaping):
            Teal-white edge — the most complex region, living inquiry.
        unbounded (low n):
            Deep indigo-void — accumulation without comprehension, cold.

    Smooth coloring uses the escape magnitude to eliminate banding.
    """
    if n == max_iterations:
        # Bounded — within the set — warm amber-gold
        return (42, 18, 8)

    # Smooth coloring: fractional iteration count
    try:
        smooth_n = n + 1 - math.log(math.log(abs(final_z) + 1e-10) + 1e-10) / math.log(2)
    except (ValueError, ZeroDivisionError):
        smooth_n = float(n)

    t = smooth_n / max_iterations  # 0.0 (escaped immediately) → 1.0 (just escaped)

    if t > 0.85:
        # Boundary region — teal-white edge — living philosophical inquiry
        s = (t - 0.85) / 0.15
        r = int(200 + 55 * s)
        g = int(220 + 35 * s)
        b = int(220 + 35 * s)
        return (r, g, b)
    else:
        # Unbounded gradient — deep indigo through amber
        # Low t = escaped quickly = cold indigo void
        # Higher t approaching boundary = warming amber
        s = t / 0.85
        r = int(8 + 180 * (s ** 2))
        g = int(4 + 80 * (s ** 1.5))
        b = int(32 + 140 * (1 - s) + 60 * s)
        return (
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
        )


# ---------------------------------------------------------------------------
# Constructor Helpers
# ---------------------------------------------------------------------------

def new_breath() -> BreathOfKo:
    """Create a fresh Breath of Ko for a new player (all densities at 0.0)."""
    return BreathOfKo()


def breath_from_densities(densities: Dict[int, float]) -> BreathOfKo:
    """
    Construct a Breath of Ko from a density mapping.
    Any missing layers default to 0.0.
    """
    breath = BreathOfKo(layer_densities=dict(densities))
    breath.update_azoth()
    return breath
