# tests/stubs/rose_stub.py
from shygazun.kernel.types.candidate import CandidateCompletion, Preconditions, PrioritySignature

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
            provenance=[{"source": "register", "kind": "rose"}],
        )

        c2 = CandidateCompletion(
            id="rose.link.beta",
            preconditions=Preconditions(
                forbids_candidates=["rose.link.alpha"]
            ),
            effects={},
            costs=[],
            priority_signature=PrioritySignature(),
            provenance=[{"source": "register", "kind": "rose"}],
        )

        return [c1, c2]

    def constrain(self, field, candidates, frontier):
        return {}  # inert on purpose

    def observe(self, field, frontier):
        return []