# tests/test_conformance_t1_t4.py
from kernel import Kernel, RoseStub, SakuraStub


def test_T1_multi_frontier_survival_via_structural_divergence():
    """
    For this minimum kernel, T1 is demonstrated by:
      - both mutually-exclusive Rose candidates remaining eligible simultaneously
      - explicit conflicts edges materialized in the CEG
    """
    k = Kernel([RoseRegister(), SakuraRegister()])

    k.place({"raw": "A"})
    res = k.evaluate_eligibility()

    eligible = res["eligible_by_frontier"]["F0"]
    ids = {c.id for c in eligible}

    assert "rose.link.alpha" in ids
    assert "rose.link.beta" in ids

    ceg = k.get_ceg()
    # Find eligibility event IDs for alpha/beta
    elig_events = [e for e in ceg["events"] if e["kind"] == "eligibility" and e["frontier_id"] == "F0"]
    alpha_e = next(e for e in elig_events if e["candidate_id"] == "rose.link.alpha")
    beta_e = next(e for e in elig_events if e["candidate_id"] == "rose.link.beta")

    # Conflicts edges must exist (both directions, deterministic convention)
    edges = [ed for ed in ceg["edges"] if ed["type"] == "conflicts"]
    assert any(ed["from_"] == alpha_e["id"] and ed["to"] == beta_e["id"] for ed in edges)
    assert any(ed["from_"] == beta_e["id"] and ed["to"] == alpha_e["id"] for ed in edges)


def test_T4_lotus_wait_never_resolves_internally_and_is_localized():
    k = Kernel([RoseRegister(), SakuraRegister()])
    k.place({"raw": "A"})

    # Run eligibility a few times; lotus-gated candidate should never be eligible
    for _ in range(3):
        res = k.evaluate_eligibility()
        eligible_ids = {c.id for c in res["eligible_by_frontier"]["F0"]}
        assert "sakura.await.lotus" not in eligible_ids

        # Must emit localized refusal
        refusals = res["refusals"]
        assert any(r["reason_code"] == "await-lotus" and r["frontier_id"] == "F0" and r["candidate_id"] == "sakura.await.lotus"
                   for r in refusals)
