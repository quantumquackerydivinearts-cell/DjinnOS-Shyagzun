# tests/conformance/test_T4_lotus_wait.py
from kernel.kernel import Kernel
from tests.stubs.sakura_stub import SakuraStub

def test_T4_lotus_never_self_resolves():
    kernel = Kernel(registers=[SakuraStub()])

    kernel.place({"raw": "B"})

    # Run eligibility multiple times
    for _ in range(3):
        result = kernel.evaluate_eligibility()

        eligible = result["eligible_by_frontier"]["F0"]
        refusals = result["refusals"]

        # Candidate is NEVER eligible
        assert eligible == []

        # Refusal must exist and be localized
        assert any(
            r["reason_code"] == "await-lotus"
            and r["candidate_id"] == "sakura.await.lotus"
            and r["frontier_id"] == "F0"
            for r in refusals
        )
