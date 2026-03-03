from __future__ import annotations

import importlib.util
import json
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping
from uuid import uuid4


@dataclass(frozen=True)
class PygameWorkerCommand:
    command_id: str
    workspace_id: str
    actor_id: str
    action_id: str
    command_kind: str
    runtime_action_kind: str
    payload: dict[str, object]
    created_at_ms: int


class PygameWorkerManager:
    """Thread-safe queue manager for handing off work to an isolated pygame worker."""

    def __init__(self, *, max_queue_size: int = 2048) -> None:
        self._queue: queue.Queue[PygameWorkerCommand] = queue.Queue(maxsize=max_queue_size)
        self._lock = threading.Lock()
        self._accepted = 0
        self._rejected = 0
        self._dequeued = 0
        self._max_queue_size = max_queue_size

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def pygame_available() -> bool:
        return importlib.util.find_spec("pygame") is not None

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "queue_size": self._queue.qsize(),
                "queue_capacity": self._max_queue_size,
                "accepted_count": self._accepted,
                "rejected_count": self._rejected,
                "dequeued_count": self._dequeued,
                "pygame_available": self.pygame_available(),
            }

    def enqueue(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        action_id: str,
        command_kind: str,
        runtime_action_kind: str,
        payload: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        cmd = PygameWorkerCommand(
            command_id=f"pgw_{uuid4().hex}",
            workspace_id=workspace_id,
            actor_id=actor_id,
            action_id=action_id,
            command_kind=command_kind,
            runtime_action_kind=runtime_action_kind,
            payload=dict(payload or {}),
            created_at_ms=self._now_ms(),
        )
        try:
            self._queue.put_nowait(cmd)
            with self._lock:
                self._accepted += 1
            accepted = True
            reason = ""
        except queue.Full:
            with self._lock:
                self._rejected += 1
            accepted = False
            reason = "queue_full"
        status = self.status()
        return {
            "accepted": accepted,
            "reason": reason,
            "command": {
                "command_id": cmd.command_id,
                "workspace_id": cmd.workspace_id,
                "actor_id": cmd.actor_id,
                "action_id": cmd.action_id,
                "command_kind": cmd.command_kind,
                "runtime_action_kind": cmd.runtime_action_kind,
                "payload": dict(cmd.payload),
                "created_at_ms": cmd.created_at_ms,
            },
            "status": status,
        }

    def dequeue_nowait(self) -> dict[str, object] | None:
        try:
            cmd = self._queue.get_nowait()
        except queue.Empty:
            return None
        with self._lock:
            self._dequeued += 1
        return {
            "command_id": cmd.command_id,
            "workspace_id": cmd.workspace_id,
            "actor_id": cmd.actor_id,
            "action_id": cmd.action_id,
            "command_kind": cmd.command_kind,
            "runtime_action_kind": cmd.runtime_action_kind,
            "payload": dict(cmd.payload),
            "created_at_ms": cmd.created_at_ms,
        }


_WORKER_MANAGER: PygameWorkerManager | None = None


def get_pygame_worker_manager() -> PygameWorkerManager:
    global _WORKER_MANAGER
    if _WORKER_MANAGER is None:
        _WORKER_MANAGER = PygameWorkerManager()
    return _WORKER_MANAGER


def _worker_main() -> int:
    """Minimal JSONL loop for an isolated pygame worker process."""
    manager = get_pygame_worker_manager()
    print(json.dumps({"event": "worker_boot", "pygame_available": manager.pygame_available()}), flush=True)
    try:
        while True:
            line = input()
            if line is None:
                break
            line = line.strip()
            if line == "":
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                print(json.dumps({"event": "error", "reason": "invalid_json"}), flush=True)
                continue
            op = str(message.get("op", "")).strip().lower()
            if op == "quit":
                print(json.dumps({"event": "quit"}), flush=True)
                return 0
            if op == "status":
                print(json.dumps({"event": "status", "status": manager.status()}), flush=True)
                continue
            if op == "dequeue_once":
                print(json.dumps({"event": "dequeue", "item": manager.dequeue_nowait()}), flush=True)
                continue
            print(json.dumps({"event": "error", "reason": "unsupported_op"}), flush=True)
    except EOFError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(_worker_main())

