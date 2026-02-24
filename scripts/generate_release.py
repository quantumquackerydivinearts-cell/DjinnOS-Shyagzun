from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _run_checked(cmd: Sequence[str], *, cwd: Path) -> None:
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        output = proc.stdout
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\n{output}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit_hash(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Unable to read git commit hash: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _git_exact_tag(repo_root: Path) -> Optional[str]:
    proc = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Unable to read git tags: {proc.stderr.strip()}")
    tags = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not tags:
        return None
    return sorted(tags)[0]


def _collect_roots(repo_root: Path) -> List[Path]:
    roots: List[Path] = []
    shygazun_root = repo_root / "shygazun"
    scripts_root = repo_root / "scripts"
    if not shygazun_root.is_dir():
        raise RuntimeError("Required path missing: shygazun/")
    if not scripts_root.is_dir():
        raise RuntimeError("Required path missing: scripts/")

    roots.append(shygazun_root)
    roots.append(scripts_root)

    top_conformance = repo_root / "conformance"
    if top_conformance.is_dir():
        roots.append(top_conformance)
    else:
        shygazun_conformance = repo_root / "shygazun" / "conformance"
        if shygazun_conformance.is_dir():
            roots.append(shygazun_conformance)
        else:
            raise RuntimeError("Required path missing: conformance/ (or shygazun/conformance/)")

    return roots


def _collect_files(repo_root: Path, roots: Sequence[Path]) -> List[Path]:
    files: List[Path] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file():
                files.append(path)
    files.sort(key=lambda p: p.relative_to(repo_root).as_posix())
    return files


def _tar_bytes_for_file(repo_root: Path, path: Path) -> Tuple[str, bytes]:
    rel = path.relative_to(repo_root).as_posix()
    data = path.read_bytes()
    return rel, data


def _build_deterministic_tar_gz(repo_root: Path, files: Sequence[Path], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as raw_fh:
        with gzip.GzipFile(fileobj=raw_fh, mode="wb", mtime=0, filename="") as gz_fh:
            with tarfile.open(fileobj=gz_fh, mode="w") as tf:
                for path in files:
                    rel, data = _tar_bytes_for_file(repo_root, path)
                    info = tarfile.TarInfo(name=rel)
                    info.size = len(data)
                    info.mtime = 0
                    info.mode = 0o644
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    tf.addfile(info, io.BytesIO(data))


def _iso_utc_now() -> str:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic sanctum release artifact.")
    parser.add_argument("version", help="Release version label (required)")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Optional conformance runner base URL override",
    )
    args = parser.parse_args()

    version = str(args.version).strip()
    if not version:
        raise RuntimeError("Version argument must be non-empty.")

    repo_root = Path(__file__).resolve().parent.parent

    _run_checked(["pytest"], cwd=repo_root)
    _run_checked(["python", "-m", "mypy", "--strict"], cwd=repo_root)

    conformance_spec = repo_root / "shygazun" / "conformance" / "v0.1.1" / "conformance.json"
    if not conformance_spec.is_file():
        raise RuntimeError(f"Conformance spec not found: {conformance_spec}")

    conformance_cmd: List[str] = [
        "python",
        "-m",
        "shygazun.conformance.runners.python.runner",
        "--spec",
        str(conformance_spec),
    ]
    if args.base_url is not None:
        conformance_cmd.extend(["--base-url", args.base_url])
    _run_checked(conformance_cmd, cwd=repo_root)

    roots = _collect_roots(repo_root)
    files = _collect_files(repo_root, roots)

    file_hashes: Dict[str, str] = {}
    rel_files: List[str] = []
    for path in files:
        rel = path.relative_to(repo_root).as_posix()
        rel_files.append(rel)
        file_hashes[rel] = _sha256_file(path)

    release_dir = repo_root / "djinn_os" / "sanctum" / "releases" / version
    release_dir.mkdir(parents=True, exist_ok=True)

    tar_path = release_dir / "release.tar.gz"
    _build_deterministic_tar_gz(repo_root, files, tar_path)
    tar_hash = _sha256_file(tar_path)

    manifest: Dict[str, Any] = {
        "version": version,
        "timestamp_utc": _iso_utc_now(),
        "git_commit": _git_commit_hash(repo_root),
        "git_tag": _git_exact_tag(repo_root),
        "python_version": sys.version,
        "included_files": rel_files,
        "file_sha256": file_hashes,
        "release_tar_sha256": tar_hash,
    }
    manifest_path = release_dir / "release_manifest.json"
    manifest_json = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    manifest_path.write_text(manifest_json, encoding="utf-8")

    sha_path = release_dir / "release.sha256"
    sha_path.write_text(f"{tar_hash}  release.tar.gz\n", encoding="utf-8")

    print(f"Release generated at: {release_dir}")
    print(f"Tarball SHA256: {tar_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
