from __future__ import annotations

from dataclasses import replace
from typing import Callable, Optional, Union

from shygazun.ide.atelier_port import AtelierPort
from shygazun.kernel.attestation import (
    Attestation,
    CandidateLike,
    Refusal,
    intent_hash_for_candidate,
)
from shygazun.kernel.types.events import AttestationEventObj


Signer = Callable[[bytes, str], str]
SignatureVerifier = Callable[[bytes, str, str], bool]


class AttestationGateway:
    """
    Agent-gateway boundary for attestation construction and submission.

    Restrictions:
    - Only constructs structural attestations
    - No semantic inference
    - No direct CEG mutation
    """

    def __init__(self, port: AtelierPort) -> None:
        self._port = port

    def build_attestation(
        self,
        *,
        field_id: str,
        clock: int,
        frontier_id: str,
        candidate_id: str,
        agent_id: str,
        candidate: CandidateLike,
    ) -> Attestation:
        if candidate.id != candidate_id:
            raise ValueError("candidate_id does not match provided candidate object")

        return Attestation(
            field_id=field_id,
            clock=clock,
            frontier_id=frontier_id,
            candidate_id=candidate_id,
            agent_id=agent_id,
            intent_hash=intent_hash_for_candidate(candidate),
            signature=None,
        )

    def sign_attestation(self, attestation: Attestation, signer: Signer) -> Attestation:
        signature = signer(attestation.canonical_payload(), attestation.agent_id)
        return replace(attestation, signature=signature)

    def submit_attestation(
        self,
        attestation: Attestation,
        *,
        require_signature: bool = False,
        signature_verifier: Optional[SignatureVerifier] = None,
    ) -> Union[AttestationEventObj, Refusal]:
        return self._port.process_attestation(
            attestation,
            require_signature=require_signature,
            signature_verifier=signature_verifier,
        )
