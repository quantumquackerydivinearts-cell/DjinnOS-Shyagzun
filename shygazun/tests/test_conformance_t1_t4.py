from dataclasses import dataclass

from shygazun.kernel.kernel import Kernel
from shygazun.kernel.register.rose_stub import RoseStub
from shygazun.kernel.register.sakura_stub import SakuraStub
from shygazun.kernel.types import Clock


@dataclass
class _Field:
    field_id: str
    clock: Clock


def test_T1_multi_frontier_survival_via_structural_divergence() -> None:
    k = Kernel(
        field=_Field(field_id="F0", clock=Clock(tick=0, causal_epoch="0")),
        registers=[RoseStub(), SakuraStub()],
    )

    k.place(raw="A")
    res = k.observe()
    ids = {c.id for c in res.eligible_by_frontier["F0"]}

    assert "rose.link.alpha" in ids
    assert "rose.link.beta" in ids

    events = list(k.get_events())
    elig_events = [e for e in events if e["kind"] == "eligibility" and e["frontier_id"] == "F0"]
    alpha_e = next(e for e in elig_events if e["candidate_id"] == "rose.link.alpha")
    beta_e = next(e for e in elig_events if e["candidate_id"] == "rose.link.beta")

    edges = [ed for ed in k.get_edges() if ed.type == "conflicts"]
    assert any(ed.from_event == alpha_e["id"] and ed.to_event == beta_e["id"] for ed in edges)
    assert any(ed.from_event == beta_e["id"] and ed.to_event == alpha_e["id"] for ed in edges)


def test_T4_lotus_wait_never_resolves_internally_and_is_localized() -> None:
    k = Kernel(
        field=_Field(field_id="F0", clock=Clock(tick=0, causal_epoch="0")),
        registers=[RoseStub(), SakuraStub()],
    )
    k.place(raw="A")

    for _ in range(3):
        res = k.observe()
        eligible_ids = {c.id for c in res.eligible_by_frontier["F0"]}
        assert "sakura.await.lotus" not in eligible_ids
        assert any(
            r["reason_code"] == "await-lotus"
            and r["frontier_id"] == "F0"
            and r["candidate_id"] == "sakura.await.lotus"
            for r in res.refusals
        )
