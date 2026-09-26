"""P5 - exact local package fixture resolution.

Resolves the requested package against a LOCAL fixture directory first (no
arbitrary downloads, nothing executed from the host project).  Records the
exact name/version, import module, source path, artifact content hash,
declared dependency metadata and transitive dependency declarations.

Connecting this phase to real PyPI metadata/artifacts is a later CAVR phase.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from shared.errors import InputError

_HASH_CHUNK = 1024 * 1024
_SKIP_DIR_NAMES = {"__pycache__", ".git", ".pytest_cache"}


@dataclass(frozen=True)
class ResolvedPackage:
    """Exact resolution of a local package fixture."""

    name: str
    version: str
    module: str
    source_dir: str
    artifact_hash: str
    files: tuple[dict, ...]
    dependencies: tuple[str, ...]
    transitive_dependencies: tuple[str, ...]
    metadata: dict

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "module": self.module,
            "source_dir": self.source_dir,
            "artifact_hash": self.artifact_hash,
            "hash_algorithm": "sha256",
            "file_count": len(self.files),
            "files": [dict(entry) for entry in self.files],
            "dependencies": list(self.dependencies),
            "transitive_dependencies": list(self.transitive_dependencies),
            "metadata": dict(self.metadata),
            "declared_only": True,
        }


def _iter_files(root: Path) -> list[Path]:
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not (_SKIP_DIR_NAMES & set(path.relative_to(root).parts))
    ]
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_package_identity(package_dir: str | Path) -> tuple[str, str, str, dict]:
    """Read just the declared identity (name, version, module, metadata).

    Used by P1/P2 (action capture and the requirement gate) so a blocked
    action never triggers full artifact analysis (hashing, file inventory).
    """
    root = Path(package_dir)
    if not root.is_dir():
        raise InputError(f"package directory not found: {root}")
    metadata_path = root / "metadata.json"
    if not metadata_path.is_file():
        raise InputError(f"package fixture is missing metadata.json: {root}")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read {metadata_path}: {exc}") from exc
    if not isinstance(metadata, dict):
        raise InputError(f"{metadata_path} must contain a JSON object")
    name = metadata.get("name")
    version = metadata.get("version")
    if not name or not version:
        raise InputError(f"{metadata_path} must declare 'name' and 'version'")
    module = str(metadata.get("module") or str(name).replace("-", "_"))
    return str(name), str(version), module, metadata


def resolve_local_package(package_dir: str | Path) -> ResolvedPackage:
    """Resolve a local package fixture directory into exact artifact facts."""
    root = Path(package_dir)
    name, version, module, metadata = read_package_identity(root)

    entries: list[dict] = []
    artifact_digest = hashlib.sha256()
    for path in _iter_files(root):
        relative = path.relative_to(root).as_posix()
        file_digest = _sha256_file(path)
        size = path.stat().st_size
        entries.append({"path": relative, "sha256": file_digest, "size": size})
        artifact_digest.update(f"{relative}:{file_digest}\n".encode("utf-8"))

    return ResolvedPackage(
        name=name,
        version=version,
        module=module,
        source_dir=str(root),
        artifact_hash=artifact_digest.hexdigest(),
        files=tuple(entries),
        dependencies=tuple(str(d) for d in metadata.get("dependencies", [])),
        transitive_dependencies=tuple(
            str(d) for d in metadata.get("transitive_dependencies", [])
        ),
        metadata=metadata,
    )
