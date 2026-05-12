"""
intel.py — Shygazun semantic substrate: Hopfield network over the byte table.

The byte table is a coordinate space defined by prime factorisation.
Candidates (akinen) are positioned by byte address; their geometric
relationships define the attractor basin topology.

Semantic queries converge to the nearest coherent candidate set via
energy descent (Giann) or temperature-weighted sampling (Keshi).

Diff-invariant kernel: W(i,j) = K(addr_j - addr_i) — the weight
between two candidates depends only on their address difference, making
the Hopfield update a 1-D convolution over semantic space.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from shygazun.kernel.constants.byte_table import SHYGAZUN_BYTE_ROWS

# ── Candidate table ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Candidate:
    addr:   int
    tongue: str
    symbol: str
    meaning: str
    lotus_gated: bool = False

_GATED_TONGUES = {"Lotus", "Cannabis"}

def _build_candidates() -> list[Candidate]:
    skip = {
        "Reserved", "MetaTopology", "MetaPhysics", "Physics", "Chemistry"
    }
    cands = []
    for row in SHYGAZUN_BYTE_ROWS:
        if row["tongue"] in skip:
            continue
        cands.append(Candidate(
            addr        = row["decimal"],
            tongue      = row["tongue"],
            symbol      = row["symbol"],
            meaning     = row["meaning"],
            lotus_gated = row["tongue"] in _GATED_TONGUES,
        ))
    return cands

CANDIDATES: list[Candidate] = _build_candidates()
N = len(CANDIDATES)  # 1358
ADDR = np.array([c.addr for c in CANDIDATES], dtype=np.float32)
TONGUE_NAMES = [c.tongue for c in CANDIDATES]

# ── Diff-invariant kernel ─────────────────────────────────────────────────────
#
# K(δ) maps a signed address difference to a weight in [0, 1].
# Different kernels define different semantic lenses.
#
# The weight matrix W is implicit: W[i,j] = K(ADDR[j] - ADDR[i]).
# Because W is a function of pairwise diffs, the Hopfield update
# h = W @ s is a (non-circular) convolution in address space.

def _kernel_giann(delta: np.ndarray) -> np.ndarray:
    """Inverse-distance: nearby candidates strongly reinforce."""
    return 1.0 / (np.abs(delta) + 1.0)

def _kernel_keshi(delta: np.ndarray, temp: float = 2.0) -> np.ndarray:
    """Exponential: temperature controls basin width."""
    return np.exp(-np.abs(delta) / (temp + 1e-9))

def _kernel_drovitth(delta: np.ndarray, window: int = 10) -> np.ndarray:
    """Periodic resonance: activates candidates at regular address intervals."""
    return (np.abs(delta) % window == 0).astype(np.float32)

def _kernel_saelith(delta: np.ndarray, threshold: float = 16.0) -> np.ndarray:
    """Step function: hard gate, only candidates within threshold."""
    return (np.abs(delta) <= threshold).astype(np.float32)

def _tongue_affinity(i: int, j: int) -> float:
    """Bonus weight for candidates in the same or adjacent tongue registers."""
    ti, tj = TONGUE_NAMES[i], TONGUE_NAMES[j]
    if ti == tj:
        return 1.0
    # Adjacent tongues share structure — boost slightly.
    return 0.3

def build_weight_matrix(
    kernel: Literal["giann", "keshi", "drovitth", "saelith"] = "giann",
    temp: float = 2.0,
    window: int = 10,
    threshold: float = 16.0,
) -> np.ndarray:
    """
    Materialise the N×N weight matrix from the diff-invariant kernel.
    Called once per query config; result can be cached for repeated queries.
    """
    delta = ADDR[None, :] - ADDR[:, None]   # shape (N, N), delta[i,j] = addr_j - addr_i

    if kernel == "giann":
        W = _kernel_giann(delta)
    elif kernel == "keshi":
        W = _kernel_keshi(delta, temp)
    elif kernel == "drovitth":
        W = _kernel_drovitth(delta, window)
    elif kernel == "saelith":
        W = _kernel_saelith(delta, threshold)
    else:
        W = _kernel_giann(delta)

    np.fill_diagonal(W, 0.0)
    return W.astype(np.float32)

# ── Hopfield relaxation ───────────────────────────────────────────────────────

def hopfield_step(s: np.ndarray, W: np.ndarray, temp: float = 0.0) -> np.ndarray:
    """One synchronous update of the state vector."""
    h = W @ s
    if temp <= 0.0:
        return np.sign(h)
    return np.tanh(h / temp)

def hopfield_converge(
    s: np.ndarray,
    W: np.ndarray,
    pinned: list[int],
    max_iter: int = 32,
    tol: float = 0.01,
    temp: float = 0.0,
) -> tuple[np.ndarray, int]:
    """
    Relax s to a fixed point, keeping pinned indices unchanged.
    Returns (final_state, iterations_taken).
    """
    s = s.copy()
    mask = np.ones(N, dtype=bool)
    for i in pinned:
        mask[i] = False

    for it in range(max_iter):
        s_new = hopfield_step(s, W, temp)
        s_new[~mask] = s[~mask]          # restore pinned
        if np.max(np.abs(s_new - s)) < tol:
            return s_new, it
        s = s_new
    return s, max_iter

# ── Query API ─────────────────────────────────────────────────────────────────

@dataclass
class QueryResult:
    active:     list[int]           # indices of activated candidates (s > 0.5)
    candidates: list[Candidate]     # the actual candidate objects
    energy:     float
    iterations: int
    state:      list[float]         # full activation vector (1358 floats)

def query_by_tongue(
    tongues: list[str],
    kernel:  Literal["giann", "keshi", "drovitth", "saelith"] = "giann",
    temp:    float = 0.0,
    window:  int   = 10,
    threshold: float = 16.0,
    max_iter: int  = 32,
) -> QueryResult:
    """
    Pin all candidates of the specified tongues to +1, weak prior -0.3 elsewhere.
    Converge to semantic fixed point.
    """
    W = build_weight_matrix(kernel, temp, window, threshold)

    s = np.full(N, -0.3, dtype=np.float32)
    pinned = []
    for i, c in enumerate(CANDIDATES):
        if c.tongue in tongues:
            s[i] = 1.0
            pinned.append(i)

    s, iters = hopfield_converge(s, W, pinned, max_iter, temp=temp)

    active = [i for i in range(N) if s[i] > 0.5]
    energy = float(-0.5 * (s @ W @ s))
    return QueryResult(
        active     = active,
        candidates = [CANDIDATES[i] for i in active],
        energy     = energy,
        iterations = iters,
        state      = s.tolist(),
    )

def query_near(
    addr: int,
    radius: int = 32,
    kernel: Literal["giann", "keshi", "drovitth", "saelith"] = "giann",
    temp:   float = 0.0,
    max_iter: int = 32,
) -> QueryResult:
    """
    Pin candidates within `radius` of `addr`, strength proportional to proximity.
    """
    W = build_weight_matrix(kernel, temp)

    s = np.full(N, -0.2, dtype=np.float32)
    pinned = []
    for i, c in enumerate(CANDIDATES):
        d = abs(c.addr - addr)
        if d <= radius:
            s[i] = 1.0 - d / (radius + 1)
            pinned.append(i)

    s, iters = hopfield_converge(s, W, pinned, max_iter, temp=temp)

    active = [i for i in range(N) if s[i] > 0.5]
    energy = float(-0.5 * (s @ W @ s))
    return QueryResult(
        active     = active,
        candidates = [CANDIDATES[i] for i in active],
        energy     = energy,
        iterations = iters,
        state      = s.tolist(),
    )

def query_diff(
    seed_addr: int,
    delta: int,
    kernel: Literal["giann", "keshi", "drovitth", "saelith"] = "giann",
    temp:   float = 1.0,
    max_iter: int = 32,
) -> QueryResult:
    """
    Semantic navigation by diff: find what is `delta` steps away from `seed_addr`.
    Delta is a signed byte-table offset — a semantic transformation operator.
    """
    target_addr = seed_addr + delta
    # Pin the seed, let the network find what's near the target.
    W = build_weight_matrix(kernel, temp)

    s = np.full(N, -0.3, dtype=np.float32)
    pinned = []
    for i, c in enumerate(CANDIDATES):
        if c.addr == seed_addr:
            s[i] = 1.0
            pinned.append(i)
        elif abs(c.addr - target_addr) <= 4:
            s[i] = 0.5   # soft attraction toward target

    s, iters = hopfield_converge(s, W, pinned, max_iter, temp=temp)

    active = [i for i in range(N) if s[i] > 0.5]
    energy = float(-0.5 * (s @ W @ s))
    return QueryResult(
        active     = active,
        candidates = [CANDIDATES[i] for i in active],
        energy     = energy,
        iterations = iters,
        state      = s.tolist(),
    )

def query_by_seeds(
    addrs:   list[int],
    kernel:  Literal["giann", "keshi", "drovitth", "saelith"] = "giann",
    temp:    float = 0.0,
    max_iter: int  = 32,
) -> QueryResult:
    """
    Pin specific byte addresses as seeds and converge to their semantic attractor.

    Used for language analysis: given akinen found in a composition, find the
    coherent semantic region they inhabit and what other candidates they pull in.
    Seeds are pinned to +1; everything else starts at a weak negative prior.
    """
    W = build_weight_matrix(kernel, temp)
    addr_set = set(addrs)

    s = np.full(N, -0.2, dtype=np.float32)
    pinned: list[int] = []
    for i, c in enumerate(CANDIDATES):
        if c.addr in addr_set:
            s[i] = 1.0
            pinned.append(i)

    s, iters = hopfield_converge(s, W, pinned, max_iter, temp=temp)

    active = [i for i in range(N) if s[i] > 0.5]
    energy = float(-0.5 * (s @ W @ s))
    return QueryResult(
        active     = active,
        candidates = [CANDIDATES[i] for i in active],
        energy     = energy,
        iterations = iters,
        state      = s.tolist(),
    )

# ── Tongue registry ───────────────────────────────────────────────────────────

def all_tongues() -> list[str]:
    seen: list[str] = []
    for c in CANDIDATES:
        if c.tongue not in seen:
            seen.append(c.tongue)
    return seen

def candidates_by_tongue(tongue: str) -> list[Candidate]:
    return [c for c in CANDIDATES if c.tongue == tongue]
