# tests/stubs/sakura_stub.py
from kernel.types import (
    CandidateCompletion,
    Preconditions,
    PrioritySignature,
    Provenance,
    LotusRequirement,
)

class SakuraStub:
    name = "sakura"

    def admit(self, fragment, field):
        return {"admitted": True, "claim_ids": ["sakura.claim"]}

    def propose(self, field, claims, frontier):
        return [
            CandidateCompletion(
                id="sakura.await.lotus",
                preconditions=Preconditions(
                    lotus_requirement=LotusRequirement(
                        kind="await_attestation",
                        attestation_tag="lotus"
                    )
                ),
                effects={},
                costs=[],
                priority_signature=PrioritySignature(
                    tail_markers=["closure"]
                ),
                provenance=[Provenance(source="register", name="sakura")],
            )
        ]

    def constrain(self, field, candidates, frontier):
        return {}

    def observe(self, field, frontier):
        return []
