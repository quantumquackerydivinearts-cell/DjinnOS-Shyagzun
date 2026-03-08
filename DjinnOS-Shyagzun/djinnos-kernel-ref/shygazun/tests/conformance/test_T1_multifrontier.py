# tests/conformance/test_T1_multifrontier.py
from kernel.kernel import Kernel
from tests.stubs.rose_stub import RoseStub

def test_T1_multifrontier_survival():
    kernel = Kernel(registers=[RoseStub()])

    # Place anything (content irrelevant)
    kernel.place({"raw": "A"})

    result = kernel.evaluate_eligibility()

    eligible = result["eligible_by_frontier"]["F0"]

    ids = {c.id for c in eligible}

    assert ids == {"rose.link.alpha", "rose.link.beta"}

    # Ensure conflict edges exist
    ceg = kernel.get_ceg()
    conflict_edges = [
        e for e in ceg["edges"] if e["type"] == "conflicts"
    ]

    assert len(conflict_edges) >= 2  # bidirectional or canonical
