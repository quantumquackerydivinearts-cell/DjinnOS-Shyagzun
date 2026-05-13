"""
kobra_vm.py — Kobra semantic VM

The minimal Kobra VM. A Kobra program is Shygazun text. Running it means:
  1. Tokenize to byte addresses (greedy longest-match against the byte table)
  2. Seed the Hopfield field from those addresses
  3. Run the field through the 12-layer Orrery
  4. The fired layers and the output field ARE the computation's result

This is the empirical prototype. We run real .ko files through it, observe
which layers fire, and let the language tell us what the execution semantics
mean. The architecture emerges from observation, not prescription.

No LLM. No external API. The language processes itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .recombination import (
    LAYERS, RecombLayer, run as orrery_run, probe as orrery_probe,
    RecombTrace, LayerFiring, elem_of_addr as _elem_of_addr_py,
)
from .roko import tokenize
from .intel import CANDIDATES

# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class LayerReading:
    rose:        str
    compound:    str
    primary:     str
    destination: str
    purpose:     str
    fired:       bool

@dataclass
class KobraResult:
    source_name:   str
    source:        str
    tokens:        list[tuple[int, str, str, str]]  # (addr, sym, tongue, meaning)
    token_count:   int
    unique_addrs:  int
    fired_layers:  list[LayerReading]
    unfired_layers: list[LayerReading]
    layers_fired:  int
    final_energy:  float
    trace:         RecombTrace

    @property
    def fired_names(self) -> list[str]:
        return [l.rose for l in self.fired_layers]

    @property
    def elemental_signature(self) -> dict[str, int]:
        """Count of elemental sub-register tokens in this program."""
        counts: dict[str, int] = {"Shak": 0, "Puf": 0, "Mel": 0, "Zot": 0, "?": 0}
        for addr, _, _, _ in self.tokens:
            e = _elem_of_addr_py(addr)
            counts[e if e else "?"] += 1
        return counts

    def _elem_of_addr_py(self, addr: int) -> Optional[str]:
        return _elem_of_addr_py(addr)

# ── Tokenizer shim ────────────────────────────────────────────────────────────

def _strip_comments(source: str) -> str:
    """Remove # comment lines from Kobra source."""
    lines = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Inline comments
        if '#' in line:
            line = line[:line.index('#')]
        lines.append(line)
    return '\n'.join(lines)

def _tokenize_kobra(source: str) -> list[tuple[int, str, str, str]]:
    """
    Tokenize Kobra source to (addr, symbol, tongue, meaning) tuples.
    Uses the same greedy longest-match tokenizer as roko.py.
    Skips Kobra structural keywords (Mavo*, Lo*, TaShyMa) only if
    they don't themselves resolve to byte table symbols — but in
    practice Mavo, Lo, Ta, Shy, Ma etc. ARE real Shygazun and will
    tokenize correctly. We let the tokenizer handle everything.
    """
    clean = _strip_comments(source)
    return tokenize(clean)

# ── Core VM ───────────────────────────────────────────────────────────────────

def kobra_run(source: str, name: str = "<source>") -> KobraResult:
    """
    Run a Kobra program through the Orrery. Returns a KobraResult
    with the full firing trace and semantic interpretation.
    """
    tokens = _tokenize_kobra(source)
    addrs  = list(dict.fromkeys(t[0] for t in tokens))  # unique, order-preserving

    if not addrs:
        # No recognized Shygazun — return empty result
        empty_layer = [
            LayerReading(
                rose=L.rose, compound=L.compound,
                primary=L.primary, destination=L.destination,
                purpose=L.purpose, fired=False,
            )
            for L in LAYERS
        ]
        # Build a minimal empty trace
        from .recombination import RecombTrace, LayerFiring
        empty_trace = RecombTrace(
            input_addrs=[], firings=[], final_state=[0.0]*len(CANDIDATES),
            final_active=[], final_energy=0.0, layers_fired=0
        )
        return KobraResult(
            source_name=name, source=source, tokens=[], token_count=0,
            unique_addrs=0, fired_layers=[], unfired_layers=empty_layer,
            layers_fired=0, final_energy=0.0, trace=empty_trace,
        )

    # Use Giann kernel (inverse-distance, global reach) so that cue addresses
    # far from explicit seeds can still activate through the semantic field.
    # Higher temp (1.5) keeps the field soft enough for crossing detection.
    trace = orrery_run(addrs, kernel="giann", temp=1.5, max_iter=48)

    fired_layers   = []
    unfired_layers = []

    for L, firing in zip(LAYERS, trace.firings):
        reading = LayerReading(
            rose        = L.rose,
            compound    = L.compound,
            primary     = L.primary,
            destination = L.destination,
            purpose     = L.purpose,
            fired       = firing.fired,
        )
        if firing.fired:
            fired_layers.append(reading)
        else:
            unfired_layers.append(reading)

    return KobraResult(
        source_name    = name,
        source         = source,
        tokens         = tokens,
        token_count    = len(tokens),
        unique_addrs   = len(addrs),
        fired_layers   = fired_layers,
        unfired_layers = unfired_layers,
        layers_fired   = trace.layers_fired,
        final_energy   = trace.final_energy,
        trace          = trace,
    )


def kobra_run_file(path: str | Path) -> KobraResult:
    """Run a .ko file through the VM."""
    p = Path(path)
    return kobra_run(p.read_text(encoding='utf-8'), name=p.name)


# ── Batch runner + comparison ─────────────────────────────────────────────────

def run_suite(paths: list[str | Path]) -> list[KobraResult]:
    """Run a set of .ko files and return results."""
    return [kobra_run_file(p) for p in paths]


def comparison_table(results: list[KobraResult]) -> str:
    """
    Render a comparison table of which layers fired across multiple programs.
    Columns = programs. Rows = layers. Fired = ● Unfired = ·
    """
    layer_names = [L.rose for L in LAYERS]
    names       = [r.source_name[:18] for r in results]

    col_w  = max(len(n) for n in names) + 2
    row_lw = 12  # rose name width

    lines = []

    # Header
    header = ' ' * row_lw + '  '
    header += ''.join(n.center(col_w) for n in names)
    lines.append(header)
    lines.append('─' * len(header))

    # Layer rows
    for i, L in enumerate(LAYERS):
        label = f"{L.rose}({L.compound})"[:row_lw].ljust(row_lw)
        row = label + '  '
        for r in results:
            fired = any(fl.rose == L.rose for fl in r.fired_layers)
            row += ('●' if fired else '·').center(col_w)
        lines.append(row)

    lines.append('─' * len(header))

    # Summary
    lines.append(' ' * (row_lw + 2) + ''.join(
        str(r.layers_fired).center(col_w) for r in results
    ))
    lines.append(' ' * (row_lw + 2) + ''.join(
        'fired'.center(col_w) for _ in results
    ))

    # Elemental signature
    lines.append('')
    lines.append('ELEMENTAL SIGNATURES')
    lines.append('─' * 40)
    for r in results:
        sig = r.elemental_signature
        total = max(1, sum(v for k, v in sig.items() if k != '?'))
        lines.append(f"  {r.source_name[:20]:<20}")
        for elem, cnt in [(k, sig[k]) for k in ('Shak','Puf','Mel','Zot')]:
            pct = int(cnt / total * 100)
            lines.append(f"    {elem:<6} {'█' * (pct // 5):<20} {pct:3}%  ({cnt} tokens)")

    return '\n'.join(lines)


def print_suite(paths: list[str | Path]) -> list[KobraResult]:
    """Run a suite, print the comparison table, return results."""
    results = run_suite(paths)
    print(comparison_table(results))
    return results


# ── Semantic interpretation ───────────────────────────────────────────────────

# What a fired layer means in Kobra semantic terms
LAYER_KOBRA_MEANING: dict[str, str] = {
    "Gaoh":    "volatile activation threshold — Air about to ignite; anticipation before state change",
    "Ao":      "Sulphur register — pattern organizing into atmosphere; directed Fire spreading outward",
    "Ye":      "Alkahest register — dissolution underway; boundaries softening; the universal solvent active",
    "Ui":      "Magma register — pattern crystallizing into permanent structure; Fire cooling into form",
    "Shu":     "Steam register — Water reaching toward Heat; pressure building from depth",
    "Kiel":    "Vapor register — memory lifting into atmosphere; held liquid becoming free",
    "Yeshu":   "Condensation register — thought precipitating; something abstract gaining weight",
    "Lao":     "Mercury register — Air making contact with Earth; messenger touching ground",
    "Shushy":  "Radiation register — stored Earth energy releasing; the stable becoming active",
    "Uinshu":  "Dust register — form dispersing; structure broadcasting outward into air",
    "Kokiel":  "Groundwater register — form dissolving into flow; Earth opening to receive Water",
    "Aonkiel": "Erosion register — Water claiming Earth; the patient settling of flow into ground",
}

def interpret(result: KobraResult) -> str:
    """Return a Kobra-semantic interpretation of a VM result."""
    lines = [f"=== {result.source_name} ==="]
    lines.append(f"Tokens: {result.token_count} ({result.unique_addrs} unique addresses)")
    lines.append(f"Layers fired: {result.layers_fired}/12")
    lines.append(f"Final energy: {result.final_energy:.3f}")
    lines.append("")

    if result.fired_layers:
        lines.append("ACTIVE CROSSINGS:")
        for lr in result.fired_layers:
            meaning = LAYER_KOBRA_MEANING.get(lr.rose, lr.purpose)
            lines.append(f"  {lr.rose:<10} {lr.compound} ({lr.primary}→{lr.destination})")
            lines.append(f"             {meaning}")
    else:
        lines.append("NO CROSSINGS ACTIVE")

    sig = result.elemental_signature
    total = max(1, sum(v for k, v in sig.items() if k != '?'))
    lines.append("")
    lines.append("ELEMENTAL BALANCE:")
    for elem in ('Shak', 'Puf', 'Mel', 'Zot'):
        cnt = sig[elem]
        pct = int(cnt / total * 100)
        bar = '█' * (pct // 5)
        lines.append(f"  {elem:<6} {bar:<20} {pct:3}%")

    return '\n'.join(lines)
