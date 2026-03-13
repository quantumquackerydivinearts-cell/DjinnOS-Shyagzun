from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class PlaceRequest(BaseModel):
    utterance: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class PlaceResponse(BaseModel):
    field_id: str
    clock: Dict[str, Any]
    placement_event: Dict[str, Any]
    observe: Dict[str, Any]


class EligibilityRequest(BaseModel):
    field_id: str
    frontier_ids: List[str]


class AttestRequest(BaseModel):
    field_id: str
    attestation: Dict[str, Any]
    target: Dict[str, Any]


class ReplayRequest(BaseModel):
    bundle: Dict[str, Any]

