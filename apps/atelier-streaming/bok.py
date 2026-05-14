"""
bok.py — BoK (BreathOfKo) trajectory tracking and Roko assessment bridge.

Each stream session accumulates a BoK trajectory — a sequence of (re, im)
complex number samples emitted by the practitioner every 30 s during a
Wunashakoun-mode session.

On session end, the trajectory is submitted to Roko for structural assessment.
Roko returns a gate level (Tiwu/Tawu/FyKo/Mowu/ZoWu) and a practice_viable
flag. Sessions at Tiwu or Tawu with entropy_ticks >= 3 are Quack-eligible.

Roko API: /v1/roko/assess  (from the Atelier API)
"""

import os
import time
import math
import aiohttp
from dataclasses import dataclass, field
from typing import Optional

ATELIER_API = os.getenv("ATELIER_API", "http://127.0.0.1:9000")

# Minimum ticks for Quack eligibility
QUACK_MIN_TICKS = 3

# Gates that permit Quack
QUACK_GATES = {"Tiwu", "Tawu"}


@dataclass
class BoKPoint:
    re:  float
    im:  float
    ts:  float = field(default_factory=time.time)


@dataclass
class BokSession:
    stream_id:       str
    artisan_id:      str
    started_at:      float = field(default_factory=time.time)
    trajectory:      list  = field(default_factory=list)
    entropy_ticks:   int   = 0
    ended_at:        Optional[float] = None
    roko_gate:       Optional[str]   = None
    quack_eligible:  bool = False
    tongue_proposal: Optional[str]   = None

    def add_point(self, re: float, im: float) -> None:
        self.trajectory.append(BoKPoint(re=re, im=im))
        self.entropy_ticks += 1

    def geometric_coherence(self) -> float:
        """
        Estimate geometric coherence of the trajectory: 0..1.
        Uses path-length stability — a coherent Wunashakoun session
        stays in bounded regions rather than wandering.

        Returns 0 if fewer than 2 points.
        """
        if len(self.trajectory) < 2:
            return 0.0
        dists = []
        for i in range(1, len(self.trajectory)):
            dr = self.trajectory[i].re - self.trajectory[i-1].re
            di = self.trajectory[i].im - self.trajectory[i-1].im
            dists.append(math.sqrt(dr*dr + di*di))
        if not dists:
            return 0.0
        mean = sum(dists) / len(dists)
        if mean == 0:
            return 1.0
        # Coefficient of variation: lower = more stable = more coherent
        variance = sum((d - mean)**2 for d in dists) / len(dists)
        std = math.sqrt(variance)
        cv  = std / mean
        return max(0.0, min(1.0, 1.0 - cv))

    def tongue_candidate(self) -> Optional[str]:
        """
        Generate a tongue-generation proposal from the BoK trajectory.
        The proposal is the mean c parameter reduced to a symbolic description.
        """
        if len(self.trajectory) < 3:
            return None
        mean_re = sum(p.re for p in self.trajectory) / len(self.trajectory)
        mean_im = sum(p.im for p in self.trajectory) / len(self.trajectory)
        r = math.sqrt(mean_re**2 + mean_im**2)
        theta = math.atan2(mean_im, mean_re) * 180 / math.pi
        return (
            f"BoK-derived candidate at c={mean_re:.4f}+{mean_im:.4f}i "
            f"(r={r:.3f}, theta={theta:.1f}°) — session of {len(self.trajectory)} samples "
            f"over {(self.ended_at or time.time()) - self.started_at:.0f}s"
        )


# ── In-memory session store ───────────────────────────────────────────────────

_sessions: dict[str, BokSession] = {}


def create_session(stream_id: str, artisan_id: str) -> BokSession:
    s = BokSession(stream_id=stream_id, artisan_id=artisan_id)
    _sessions[stream_id] = s
    return s


def get_session(stream_id: str) -> Optional[BokSession]:
    return _sessions.get(stream_id)


def add_point(stream_id: str, re: float, im: float) -> Optional[BokSession]:
    s = _sessions.get(stream_id)
    if s:
        s.add_point(re, im)
    return s


# ── Roko assessment ───────────────────────────────────────────────────────────

async def assess_session(stream_id: str) -> dict:
    """
    End the session, compute geometric coherence, and request Roko assessment.
    Returns a summary dict suitable for the Broadcast panel's SessionSummary.
    """
    s = _sessions.get(stream_id)
    if not s:
        return {"error": "session not found"}

    s.ended_at = time.time()
    coherence  = s.geometric_coherence()

    # Call Roko assess endpoint
    roko_gate       = "ZoWu"
    practice_viable = False
    try:
        domain_hint = f"stream-{stream_id}-bok-coherence-{coherence:.2f}"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ATELIER_API}/v1/roko/assess",
                json={"domain": domain_hint, "flags": {"bok_coherence": coherence}},
                timeout=aiohttp.ClientTimeout(total=8),
            ) as r:
                if r.status == 200:
                    d       = await r.json()
                    roko_gate       = d.get("gate", "ZoWu")
                    practice_viable = d.get("practice_viable", False)
    except Exception:
        pass

    s.roko_gate      = roko_gate
    s.quack_eligible = (
        roko_gate in QUACK_GATES
        and s.entropy_ticks >= QUACK_MIN_TICKS
        and practice_viable
    )
    s.tongue_proposal = s.tongue_candidate() if s.quack_eligible else None

    return {
        "roko_gate":        roko_gate,
        "practice_viable":  practice_viable,
        "quack_eligible":   s.quack_eligible,
        "entropy_ticks":    s.entropy_ticks,
        "bok_coherence":    round(coherence, 3),
        "bok_trajectory":   [{"re": p.re, "im": p.im, "ts": p.ts}
                              for p in s.trajectory],
        "tongue_proposal":  s.tongue_proposal,
    }


def cleanup(stream_id: str) -> None:
    _sessions.pop(stream_id, None)
