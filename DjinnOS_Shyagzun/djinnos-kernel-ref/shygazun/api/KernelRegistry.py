# shygazun/api/state.py
from __future__ import annotations

from typing import Dict

from shygazun.kernel.kernel import Kernel
from shygazun.kernel.types.field import Field
from shygazun.kernel.types.clock import Clock
from shygazun.kernel.types.frontier import Frontier
from shygazun.kernel.types.lotus import LotusState


class KernelRegistry:
    def __init__(self) -> None:
        self._kernels: dict[str, Kernel] = {}

    def get_or_create_kernel(self, field_id: str) -> Kernel:
        kernel = self._kernels.get(field_id)
        if kernel:
            return kernel

        field = Field(
            field_id=field_id,
            clock=Clock(tick=0, causal_epoch="genesis"),
            tensions={},
            gates={},
            obligations={},
            atoms={},
            lotus=LotusState(attestations=[], status="opaque"),
        )

        kernel = Kernel(
            field=field,
            frontiers=[
                Frontier(
                    id="F0",
                    event_ids=[],
                    status="active",
                    inconsistency_proof=None,
                )
            ],
            registers=[],
        )

        self._kernels[field_id] = kernel
        return kernel
