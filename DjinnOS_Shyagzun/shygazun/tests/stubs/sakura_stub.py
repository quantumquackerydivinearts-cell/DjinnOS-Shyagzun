# tests/stubs/sakura_stub.py
from shygazun.kernel.types.candidate import CandidateCompletion, Preconditions, PrioritySignature

class SakuraStub:
    name = "sakura"

    def admit(self, fragment, field):
        return {"admitted": True, "claim_ids": ["sakura.claim"]}

    def propose(self, field, claims, frontier):
        return [
            CandidateCompletion(
                id="sakura.await.lotus",
                preconditions=Preconditions(
                    lotus_requirement={"kind": "await_attestation", "attestation_tag": "lotus"}
                ),
                effects={},
                costs=[],
                priority_signature=PrioritySignature(
                    tail_markers=["closure"]
                ),
                provenance=[{"source": "register", "kind": "sakura"}],
            )
        ]

    def constrain(self, field, candidates, frontier):
        return {}

    def observe(self, field, frontier):
        return []