# tests/stubs/rose_stub.py
from kernel.types import (
    CandidateCompletion,
    Preconditions,
    PrioritySignature,
    Provenance,
)

class RoseStub:
    name = "rose"

    def admit(self, fragment, field):
        return {"admitted": True, "claim_ids": ["rose.claim"]}

    def propose(self, field, claims, frontier):
        c1 = CandidateCompletion(
            id="rose.link.alpha",
            preconditions=Preconditions(
                forbids_candidates=["rose.link.beta"]
            ),
            effects={},
            costs=[],
            priority_signature=PrioritySignature(),
            provenance=[Provenance(source="register", name="rose")],
        )

        c2 = CandidateCompletion(
            id="rose.link.beta",
            preconditions=Preconditions(
                forbids_candidates=["rose.link.alpha"]
            ),
            effects={},
            costs=[],
            priority_signature=PrioritySignature(),
            provenance=[Provenance(source="register", name="rose")],
        )

        return [c1, c2]

    def constrain(self, field, candidates, frontier):
        return {}  # inert on purpose

    def observe(self, field, frontier):
        return []
