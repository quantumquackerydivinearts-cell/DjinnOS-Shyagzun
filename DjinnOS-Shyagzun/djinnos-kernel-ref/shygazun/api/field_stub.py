# shygazun/api/field_stub.py
from dataclasses import dataclass
from shygazun.kernel.types.field import Field
from shygazun.kernel.types.clock import Clock


@dataclass
class FieldStub:
    """
    API-layer wrapper around kernel Field.
    Mutable shell, immutable core.
    """
    _field: Field

    @property
    def field_id(self) -> str:
        return self._field.field_id

    @property
    def clock(self) -> Clock:
        return self._field.clock
