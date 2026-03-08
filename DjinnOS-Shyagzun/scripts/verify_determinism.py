from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Sequence, Tuple, cast


@contextmanager
def managed_kernel_service(repo_root: Path, base_url: str) -> Iterator[None]:
    proc = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "shygazun.kernel_service:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        wait_for_service(base_url)
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def wait_for_service(base_url: str, timeout_sec: float = 20.0) -> None:
    deadline = time.time() + timeout_sec
    url = f"{base_url}/events"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                status = getattr(resp, "status", 200)
                if int(status) == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ValueError):
            time.sleep(0.2)
    raise RuntimeError(f"Service did not start in time at {base_url}")


def run_checked(cmd: Sequence[str], cwd: Path) -> None:
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\n{proc.stdout}")


def http_get_bytes(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=15.0) as resp:
            return cast(bytes, resp.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET failed: {url}") from exc


def http_post_json(url: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url=url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            data = resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"POST failed: {url}") from exc
    try:
        obj: Any = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid JSON response from {url}") from exc
    if not isinstance(obj, dict):
        raise RuntimeError(f"Expected object response from {url}")
    return obj


def run_conformance(repo_root: Path, base_url: str, conformance_file: Path) -> None:
    run_checked(
        [
            "python",
            "-m",
            "shygazun.conformance.runners.python.runner",
            "--base-url",
            base_url,
            "--file",
            str(conformance_file),
        ],
        cwd=repo_root,
    )


def replay_drift_test(repo_root: Path, base_url: str, conformance_file: Path) -> Tuple[bool, str, str]:
    a_path = repo_root / "tmp_events_A_raw.json"
    b_path = repo_root / "tmp_events_B_raw.json"
    with managed_kernel_service(repo_root, base_url):
        run_conformance(repo_root, base_url, conformance_file)
        a_bytes = http_get_bytes(f"{base_url}/events")
        a_path.write_bytes(a_bytes)
    with managed_kernel_service(repo_root, base_url):
        run_conformance(repo_root, base_url, conformance_file)
        b_bytes = http_get_bytes(f"{base_url}/events")
        b_path.write_bytes(b_bytes)

    return (
        a_bytes == b_bytes,
        hashlib.sha256(a_bytes).hexdigest(),
        hashlib.sha256(b_bytes).hexdigest(),
    )


def concurrency_test(repo_root: Path, base_url: str, calls: int) -> Tuple[bool, bool]:
    with managed_kernel_service(repo_root, base_url):
        def place(i: int) -> None:
            http_post_json(f"{base_url}/place", {"raw": f"rapid-{i}"})

        with ThreadPoolExecutor(max_workers=min(20, calls)) as executor:
            list(executor.map(place, range(calls)))

        events_raw = http_get_bytes(f"{base_url}/events")
    obj: Any = json.loads(events_raw.decode("utf-8"))
    if not isinstance(obj, list):
        raise RuntimeError("/events response is not a list")

    ids: List[str] = []
    ticks: List[int] = []
    for evt in obj:
        if not isinstance(evt, dict):
            continue
        evt_id = evt.get("id")
        if isinstance(evt_id, str):
            ids.append(evt_id)
        at_obj = evt.get("at")
        if isinstance(at_obj, dict):
            tick = at_obj.get("tick")
            if isinstance(tick, int):
                ticks.append(tick)

    unique_ids = len(ids) == len(set(ids))
    if not ticks:
        contiguous_ticks = True
    else:
        tick_set = sorted(set(ticks))
        contiguous_ticks = tick_set == list(range(1, tick_set[-1] + 1))
    return unique_ids, contiguous_ticks


def vitriol_non_interference(repo_root: Path, base_url: str, conformance_file: Path) -> None:
    vitriol_path = repo_root / "shygazun" / "kernel" / "policy" / "vitriol_cache.py"
    if not vitriol_path.is_file():
        raise RuntimeError(f"Missing vitriol module: {vitriol_path}")
    with managed_kernel_service(repo_root, base_url):
        run_conformance(repo_root, base_url, conformance_file)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run determinism verification checks.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Kernel service base URL",
    )
    parser.add_argument(
        "--file",
        default="shygazun/conformance/v0.1.1/conformance.json",
        help="Conformance file path",
    )
    parser.add_argument(
        "--concurrency-calls",
        type=int,
        default=50,
        help="Number of rapid /place calls",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    conformance_file = (repo_root / args.file).resolve()
    if not conformance_file.is_file():
        raise RuntimeError(f"Conformance file not found: {conformance_file}")
    if args.concurrency_calls < 1:
        raise RuntimeError("--concurrency-calls must be >= 1")

    replay_ok, sha_a, sha_b = replay_drift_test(repo_root, args.base_url, conformance_file)
    unique_ids, contiguous_ticks = concurrency_test(repo_root, args.base_url, args.concurrency_calls)
    vitriol_non_interference(repo_root, args.base_url, conformance_file)

    print(f"REPLAY_BYTE_IDENTICAL={replay_ok}")
    print(f"REPLAY_A_SHA256={sha_a}")
    print(f"REPLAY_B_SHA256={sha_b}")
    print(f"CONCURRENCY_UNIQUE_IDS={unique_ids}")
    print(f"CONCURRENCY_CONTIGUOUS_TICKS={contiguous_ticks}")
    print("VITRIOL_NON_INTERFERENCE=PASS")

    if not replay_ok:
        raise RuntimeError("Replay outputs are not byte-identical")
    if not unique_ids:
        raise RuntimeError("Duplicate event IDs detected under concurrency load")
    if not contiguous_ticks:
        raise RuntimeError("Non-contiguous clock ticks detected under concurrency load")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
