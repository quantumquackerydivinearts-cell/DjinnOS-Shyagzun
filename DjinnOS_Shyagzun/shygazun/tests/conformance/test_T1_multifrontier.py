from dataclasses import dataclass

from shygazun.kernel.kernel import Kernel
from shygazun.kernel.register.rose_stub import RoseStub
from shygazun.kernel.types import Clock


@dataclass
class _Field:
    field_id: str
    clock: Clock


def test_T1_multifrontier_survival() -> None:
    kernel = Kernel(
        field=_Field(field_id="F0", clock=Clock(tick=0, causal_epoch="0")),
        registers=[RoseStub()],
    )

    kernel.place(raw="A")
    result = kernel.observe()
    eligible = result.eligible_by_frontier["F0"]
    ids = {c.id for c in eligible}
    assert ids == {"rose.link.alpha", "rose.link.beta"}

    conflict_edges = [e for e in kernel.get_edges() if e.type == "conflicts"]
    assert len(conflict_edges) >= 1
