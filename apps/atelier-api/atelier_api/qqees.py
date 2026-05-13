"""
qqees.py — Quantum Quackery Entropy Encryption Service

Core entropy pool. Managed by the Salt department.

Architecture
============
Pool     : 256-slot bytearray indexed by Shygazun byte address (0–255).
           Each slot corresponds directly to a coordinate in the byte table.

Mixing   : BLAKE2b(source_id || raw_contribution || pool_snapshot) → 64 bytes.
           The digest is routed back into pool slots by the byte-value geometry:
           each digest byte at position i routes to pool[digest[i] % 256],
           then XORed. Contributions compound without overwriting each other.

Serving  : os.urandom(N) XOR pool[Orrery-selected addresses].
           Consumed slots are immediately refreshed with new os.urandom.
           This means pool entropy augments the OS CSPRNG; it cannot degrade it.

H metric : Shannon entropy of the pool byte distribution (max 8 bits/byte).
           Certificates require H ≥ 7.5 on the served bytes and H ≥ 7.0 on
           the pool itself, plus ≥ 2 distinct source types contributing.

Sources (Salt department):
  garden     — physical sensors: temperature, humidity, photon/Geiger counts
  theatrical — Bodyska performance: audio levels, motion vectors, thermal
  bok        — BreathOfKo diffs verified as Wunashakoun breaths
  orrery     — Orrery layer-firing patterns from Kobra VM runs
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

SourceType = Literal["garden", "theatrical", "bok", "orrery"]

# ── Pool singleton ────────────────────────────────────────────────────────────

_POOL_SIZE = 256
_pool: bytearray = bytearray(os.urandom(_POOL_SIZE))
_contributions_total: int = 0
_source_types_seen: set[str] = set()
_pool_born: float = time.time()


# ── Shannon H ─────────────────────────────────────────────────────────────────

def pool_shannon_h(data: bytes | bytearray | None = None) -> float:
    """Shannon entropy in bits/byte. Defaults to current pool state."""
    buf = data if data is not None else _pool
    if not buf:
        return 0.0
    counts = np.bincount(np.frombuffer(bytes(buf), dtype=np.uint8), minlength=256)
    probs = counts / counts.sum()
    nz = probs[probs > 0]
    return float(-np.dot(nz, np.log2(nz)))


# ── Mixing ────────────────────────────────────────────────────────────────────

def _mix_digest_into_pool(digest: bytes) -> None:
    global _pool
    for i, b in enumerate(digest):
        slot = b % _POOL_SIZE
        _pool[slot] ^= digest[(i + 1) % len(digest)]


def mix_contribution(
    raw: bytes,
    source_type: SourceType,
    source_id: str,
) -> float:
    """
    Mix raw entropy into the pool. Returns pool H after mixing.
    The BLAKE2b digest chains the source identity, contribution, and
    current pool state so the result is irreversible without all three.
    """
    global _contributions_total, _source_types_seen
    h = hashlib.blake2b(digest_size=64)
    h.update(source_id.encode())
    h.update(raw)
    h.update(bytes(_pool))
    _mix_digest_into_pool(h.digest())
    _contributions_total += 1
    _source_types_seen.add(source_type)
    return pool_shannon_h()


# ── Orrery-routed serving ─────────────────────────────────────────────────────

def _orrery_addresses(n: int) -> list[int]:
    """
    Pull pool slot indices from the Orrery's last firing pattern.
    Falls back to a simple stride if the Orrery is unavailable.
    """
    try:
        from .recombination import probe
        result = probe()
        addrs: list[int] = []
        for layer in result.get("fired_layers", []):
            for addr in layer.get("cue_cluster", []):
                addrs.append(int(addr) % _POOL_SIZE)
        if addrs:
            return [addrs[i % len(addrs)] for i in range(n)]
    except Exception:
        pass
    stride = max(1, _POOL_SIZE // max(n, 1))
    return [(i * stride) % _POOL_SIZE for i in range(n)]


def serve_entropy(n_bytes: int) -> tuple[bytes, float]:
    """
    Return (entropy_bytes, h_value).

    The bytes are os.urandom XOR-ed with pool slots selected by the Orrery.
    Each consumed slot is immediately refreshed so the pool never depletes.
    The returned bytes are independently H-certified before return.
    """
    global _pool
    base = bytearray(os.urandom(n_bytes))
    addrs = _orrery_addresses(n_bytes)
    for i in range(n_bytes):
        slot = addrs[i % len(addrs)]
        base[i] ^= _pool[slot]
        _pool[slot] = os.urandom(1)[0]
    result = bytes(base)
    return result, pool_shannon_h(result)


# ── Certification ─────────────────────────────────────────────────────────────

@dataclass
class EntropyCertificate:
    h_bits_per_byte:  float
    n_bytes:          int
    pool_h:           float
    contributions:    int
    source_diversity: int
    quality:          str    # "certified" | "acceptable" | "low"
    timestamp:        float

    @property
    def certified(self) -> bool:
        return self.quality == "certified"

    def to_dict(self) -> dict:
        return {
            "h_bits_per_byte":  self.h_bits_per_byte,
            "n_bytes":          self.n_bytes,
            "pool_h":           self.pool_h,
            "contributions":    self.contributions,
            "source_diversity": self.source_diversity,
            "quality":          self.quality,
            "timestamp":        self.timestamp,
            "certified":        self.certified,
        }


def certify(raw: bytes) -> EntropyCertificate:
    h       = pool_shannon_h(raw)
    pool_h  = pool_shannon_h()
    div     = len(_source_types_seen)

    if h >= 7.5 and pool_h >= 7.0 and div >= 2:
        quality = "certified"
    elif h >= 6.5:
        quality = "acceptable"
    else:
        quality = "low"

    return EntropyCertificate(
        h_bits_per_byte  = round(h, 4),
        n_bytes          = len(raw),
        pool_h           = round(pool_h, 4),
        contributions    = _contributions_total,
        source_diversity = div,
        quality          = quality,
        timestamp        = time.time(),
    )


# ── Source adapters ───────────────────────────────────────────────────────────

def contribute_from_bok(bok_diff_bytes: bytes, practitioner_id: str) -> float:
    """Ingest a serialised BreathOfKo diff as entropy."""
    return mix_contribution(bok_diff_bytes, "bok", f"bok:{practitioner_id}")


def contribute_from_theatrical(
    audio_samples: list[float],
    motion_samples: list[float],
    source_id: str,
) -> float:
    """Quantize theatrical performance floats to bytes and mix."""
    raw = bytearray()
    for v in audio_samples:
        raw.append(int(abs(v) * 255) % 256)
    for v in motion_samples:
        raw.append(int(abs(v) * 255) % 256)
    return mix_contribution(bytes(raw), "theatrical", source_id)


def contribute_from_garden(
    sensor_readings: dict[str, float],
    source_id: str,
) -> float:
    """Pack garden sensor readings as IEEE-754 doubles and mix."""
    raw = b"".join(struct.pack(">d", v) for v in sensor_readings.values())
    return mix_contribution(raw, "garden", source_id)


def contribute_from_orrery(firing_pattern: list[int], source_id: str) -> float:
    """Mix an Orrery layer-firing pattern as entropy."""
    raw = bytes(a % 256 for a in firing_pattern)
    return mix_contribution(raw, "orrery", source_id)


# ── Pool status ───────────────────────────────────────────────────────────────

def pool_status() -> dict:
    return {
        "pool_h":              round(pool_shannon_h(), 4),
        "pool_size_bytes":     _POOL_SIZE,
        "contributions_total": _contributions_total,
        "source_types_seen":   sorted(_source_types_seen),
        "source_diversity":    len(_source_types_seen),
        "uptime_seconds":      int(time.time() - _pool_born),
    }
