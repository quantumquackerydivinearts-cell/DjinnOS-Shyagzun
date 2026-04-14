from dataclasses import dataclass

from shygazun.kernel.kernel import Kernel
from shygazun.kernel.register.sakura_stub import SakuraStub
from shygazun.kernel.types import Clock


@dataclass
class _Field:
    field_id: str
    clock: Clock


def test_T4_lotus_never_self_resolves() -> None:
    kernel = Kernel(
        field=_Field(field_id="F0", clock=Clock(tick=0, causal_epoch="0")),
        registers=[SakuraStub()],  # type: ignore[list-item]
    )
    kernel.place(raw="B")

    for _ in range(3):
        result = kernel.observe()
        assert result.eligible_by_frontier["F0"] == []
        assert any(
            r["reason_code"] == "await-lotus"
            and r["candidate_id"] == "sakura.await.lotus"
            and r["frontier_id"] == "F0"
            for r in result.refusals
        )
