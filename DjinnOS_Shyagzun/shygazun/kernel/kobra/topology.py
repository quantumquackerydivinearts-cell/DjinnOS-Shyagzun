"""
shygazun/kernel/kobra/topology.py
==================================
Execution topology — structural connectivity of Kobra execution states.

An execution topology is the directed graph of how Resolved, Echo, and
FrontierOpen states connect to each other within and across expressions.
The qqva relevance layer (which handles Fold/Topology/Phase/Gradient/
Curvature tongue declarations) builds on this base graph.

Key concepts
------------
  ExecutionNode  — a single execution state in the graph.
  ExecutionEdge  — a directed connection between two nodes, labelled by
                   the kind of relationship: sequential, parallel,
                   witness (attestation resolved a FrontierOpen), or
                   echo_carry (an Echo floating forward as a live object).
  ExecutionTopology — the full graph for a scene or expression.

Topology kinds for a subgraph (how a set of nodes is shaped):
  LINEAR    — single chain, no branching.
  CYCLIC    — closes back on itself (e.g. Excavata tongue Möbius).
  BRANCHING — one node fans out to multiple successors.
  FRONTIER  — a FrontierOpen node with two parallel branches live.
  VOID      — empty or unreachable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Iterator, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Topology shape classification
# ---------------------------------------------------------------------------

class TopologyKind(str, Enum):
    LINEAR   = "linear"
    CYCLIC   = "cyclic"
    BRANCHING = "branching"
    FRONTIER = "frontier"   # live FrontierOpen with two unattested branches
    VOID     = "void"


# ---------------------------------------------------------------------------
# Edge kinds
# ---------------------------------------------------------------------------

class EdgeKind(str, Enum):
    SEQUENTIAL  = "sequential"   # A then B in a KobraSequence
    PARALLEL    = "parallel"     # A and B in a FrontierOpen (both live)
    WITNESS     = "witness"      # attestation that resolved a FrontierOpen
    ECHO_CARRY  = "echo_carry"   # an Echo carried forward as a live object
    SUBSTRUCTURE = "substructure" # header → body in a SubStructure


# ---------------------------------------------------------------------------
# Nodes and edges
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionNode:
    """
    A single execution state in the topology graph.

    ``node_id``    is a caller-assigned stable identifier (e.g. an expression
                   address or a hash of the source span).
    ``state_type`` is one of "resolved", "echo", "frontier".
    ``deliberate`` mirrors FrontierOpen.deliberate — True for Cannabis Tongue
                   intentional ambiguity, False for accidental parse ambiguity.
    ``source``     is the source text span that produced this state.
    """
    node_id:    str
    state_type: str          # "resolved" | "echo" | "frontier"
    deliberate: bool = False
    source:     str  = ""


@dataclass(frozen=True)
class ExecutionEdge:
    """
    A directed connection between two execution nodes.

    ``from_id`` → ``to_id`` with ``kind`` labelling the relationship.
    ``witness_candidate`` is set when kind==WITNESS and indicates which
    candidate was attested: "a" or "b".
    """
    from_id:           str
    to_id:             str
    kind:              EdgeKind
    witness_candidate: Optional[str] = None   # "a" | "b" | None


# ---------------------------------------------------------------------------
# Execution topology
# ---------------------------------------------------------------------------

@dataclass
class ExecutionTopology:
    """
    Full directed graph of execution states for a scene or expression.

    Nodes and edges are mutable during construction; call ``freeze()`` to
    obtain an immutable snapshot.
    """
    topology_id: str
    nodes: Dict[str, ExecutionNode] = field(default_factory=dict)
    # adjacency: from_id → list of edges
    _adj:  Dict[str, List[ExecutionEdge]] = field(
        default_factory=dict, repr=False
    )

    def add_node(self, node: ExecutionNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: ExecutionEdge) -> None:
        self._adj.setdefault(edge.from_id, []).append(edge)

    def successors(self, node_id: str) -> List[ExecutionNode]:
        edges = self._adj.get(node_id, [])
        return [
            self.nodes[e.to_id]
            for e in edges
            if e.to_id in self.nodes
        ]

    def edges_from(self, node_id: str) -> List[ExecutionEdge]:
        return list(self._adj.get(node_id, []))

    def frontier_nodes(self) -> List[ExecutionNode]:
        return [n for n in self.nodes.values() if n.state_type == "frontier"]

    def echo_nodes(self) -> List[ExecutionNode]:
        return [n for n in self.nodes.values() if n.state_type == "echo"]

    def classify(self) -> TopologyKind:
        """
        Classify the overall shape of this topology.
        Returns VOID for an empty graph.
        """
        if not self.nodes:
            return TopologyKind.VOID
        if any(n.state_type == "frontier" for n in self.nodes.values()):
            return TopologyKind.FRONTIER
        all_from: FrozenSet[str] = frozenset(self._adj.keys())
        all_to: FrozenSet[str] = frozenset(
            e.to_id
            for edges in self._adj.values()
            for e in edges
        )
        if all_from & all_to:
            return TopologyKind.CYCLIC
        max_out = max(
            (len(edges) for edges in self._adj.values()), default=0
        )
        if max_out > 1:
            return TopologyKind.BRANCHING
        return TopologyKind.LINEAR

    def iter_paths(
        self, start_id: str
    ) -> Iterator[Tuple[ExecutionNode, ...]]:
        """
        Yield all paths from ``start_id`` as tuples of ExecutionNodes.
        Cuts at cycles (revisited nodes) and at a depth limit of 64.
        """
        def _walk(
            current: str,
            visited: Tuple[str, ...],
        ) -> Iterator[Tuple[ExecutionNode, ...]]:
            if len(visited) >= 64:
                yield tuple(self.nodes[v] for v in visited)
                return
            edges = self._adj.get(current, [])
            if not edges:
                yield tuple(self.nodes[v] for v in visited)
                return
            for edge in edges:
                nxt = edge.to_id
                if nxt in visited or nxt not in self.nodes:
                    yield tuple(self.nodes[v] for v in visited)
                    continue
                yield from _walk(nxt, visited + (nxt,))

        if start_id not in self.nodes:
            return
        yield from _walk(start_id, (start_id,))


# ---------------------------------------------------------------------------
# Builder utilities
# ---------------------------------------------------------------------------

def build_sequential_topology(
    topology_id: str,
    nodes: List[ExecutionNode],
) -> ExecutionTopology:
    """
    Build a LINEAR topology from an ordered list of nodes.
    Adjacent nodes are connected with SEQUENTIAL edges.
    """
    topo = ExecutionTopology(topology_id=topology_id)
    for node in nodes:
        topo.add_node(node)
    for i in range(len(nodes) - 1):
        topo.add_edge(ExecutionEdge(
            from_id=nodes[i].node_id,
            to_id=nodes[i + 1].node_id,
            kind=EdgeKind.SEQUENTIAL,
        ))
    return topo


def build_frontier_topology(
    topology_id: str,
    frontier_node: ExecutionNode,
    candidate_a: ExecutionNode,
    candidate_b: ExecutionNode,
) -> ExecutionTopology:
    """
    Build a FRONTIER topology from a FrontierOpen node and its two candidates.
    Both candidates are connected with PARALLEL edges.
    """
    topo = ExecutionTopology(topology_id=topology_id)
    topo.add_node(frontier_node)
    topo.add_node(candidate_a)
    topo.add_node(candidate_b)
    topo.add_edge(ExecutionEdge(
        from_id=frontier_node.node_id,
        to_id=candidate_a.node_id,
        kind=EdgeKind.PARALLEL,
    ))
    topo.add_edge(ExecutionEdge(
        from_id=frontier_node.node_id,
        to_id=candidate_b.node_id,
        kind=EdgeKind.PARALLEL,
    ))
    return topo