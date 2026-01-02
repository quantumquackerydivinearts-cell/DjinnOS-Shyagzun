from dataclasses import dataclass

@dataclass(frozen=True)
class Clock:
    tick: int
    causal_epoch: str
