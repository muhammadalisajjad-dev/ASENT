"""M1 - repository / diff capture.

Prototype input adapter: compares a trusted BASELINE directory against a
CANDIDATE directory (controlled fixtures in this slice; a live coding-agent
hook is future work).  Records identifiers/hashes, changed files, unified
diff hunks and changed line ranges.

The candidate is never treated as trusted - it only becomes evidence after
the rest of the pipeline examines it.
"""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import hashlib
import re
from pathlib import Path

from shared.errors import InputError

_SKIP_DIR_NAMES = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache"}
_TEXT_SUFFIXES = {".py", ".txt", ".md", ".json", ".cfg", ".ini", ".toml", ".html", ".js"}
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _iter_files(root: Path) -> list[Path]:
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and not (_SKIP_DIR_NAMES & set(path.relative_to(root).parts))
    ]
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_identity(root: Path) -> tuple[str, tuple[dict, ...]]:
    """Stable identity of a directory tree: sha256 over sorted file digests."""
    if not root.is_dir():
        raise InputError(f"directory not found: {root}")
    entries: list[dict] = []
    digest = hashlib.sha256()
    for path in _iter_files(root):
        relative = path.relative_to(root).as_posix()
        file_digest = _sha256_file(path)
        entries.append(
            {"path": relative, "sha256": file_digest, "size": path.stat().st_size}
        )
        digest.update(f"{relative}:{file_digest}\n".encode("utf-8"))
    return digest.hexdigest(), tuple(entries)


def _read_text(path: Path) -> str | None:
    if path.suffix.lower() not in _TEXT_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _changed_ranges(unified: str) -> tuple[dict, ...]:
    ranges = []
    for line in unified.splitlines():
        match = _HUNK_RE.match(line)
        if not match:
            continue
        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        new_start = int(match.group(3))
        new_count = int(match.group(4) or "1")
        ranges.append(
            {
                "old_start": old_start,
                "old_end": old_start + max(old_count, 1) - 1 if old_count else old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_end": new_start + max(new_count, 1) - 1 if new_count else new_start,
                "new_count": new_count,
            }
        )
    return tuple(ranges)


def _diff_line_numbers(unified: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Exact changed line numbers from a unified diff body.

    Hunk header ranges include unchanged context lines; downstream analysis
    must only see lines that were genuinely added or removed.
    """
    added: list[int] = []
    removed: list[int] = []
    old_no: int | None = None
    new_no: int | None = None
    in_hunk = False
    for line in unified.splitlines():
        match = _HUNK_RE.match(line)
        if match:
            old_no = int(match.group(1))
            new_no = int(match.group(3))
            in_hunk = True
            continue
        if not in_hunk or old_no is None or new_no is None:
            continue
        if line.startswith("+"):
            added.append(new_no)
            new_no += 1
        elif line.startswith("-"):
            removed.append(old_no)
            old_no += 1
        elif line.startswith("\\"):
            continue
        else:
            old_no += 1
            new_no += 1
    return tuple(added), tuple(removed)


@dataclass(frozen=True)
class FileChange:
    """One changed file between baseline and candidate."""

    path: str
    change_type: str  # "added" | "removed" | "modified"
    unified_diff: str
    changed_ranges: tuple[dict, ...]
    text: bool

    @property
    def changed_line_numbers(self) -> tuple[int, ...]:
        """Candidate-side added line numbers (empty for removals)."""
        added, _ = _diff_line_numbers(self.unified_diff)
        return tuple(n for n in added if n > 0)

    @property
    def removed_line_numbers(self) -> tuple[int, ...]:
        """Baseline-side removed line numbers."""
        _, removed = _diff_line_numbers(self.unified_diff)
        return tuple(n for n in removed if n > 0)

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "change_type": self.change_type,
            "unified_diff": self.unified_diff,
            "changed_ranges": [dict(r) for r in self.changed_ranges],
            "changed_line_numbers": list(self.changed_line_numbers),
            "text": self.text,
        }


@dataclass(frozen=True)
class DiffCapture:
    """M1 output: baseline/candidate identity plus the raw change set."""

    baseline_dir: str
    candidate_dir: str
    baseline_id: str
    candidate_id: str
    baseline_files: tuple[dict, ...]
    candidate_files: tuple[dict, ...]
    changed_files: tuple[FileChange, ...]

    @property
    def changed_paths(self) -> tuple[str, ...]:
        return tuple(change.path for change in self.changed_files)

    def as_dict(self) -> dict:
        return {
            "baseline": {
                "dir": self.baseline_dir,
                "id": self.baseline_id,
                "file_count": len(self.baseline_files),
            },
            "candidate": {
                "dir": self.candidate_dir,
                "id": self.candidate_id,
                "file_count": len(self.candidate_files),
            },
            "changed_files": [change.as_dict() for change in self.changed_files],
            "changed_paths": list(self.changed_paths),
        }


def capture_diff(baseline_dir: str | Path, candidate_dir: str | Path) -> DiffCapture:
    """Capture the change set between the trusted baseline and the candidate."""
    baseline = Path(baseline_dir)
    candidate = Path(candidate_dir)
    baseline_id, baseline_files = tree_identity(baseline)
    candidate_id, candidate_files = tree_identity(candidate)

    baseline_map = {entry["path"]: entry for entry in baseline_files}
    candidate_map = {entry["path"]: entry for entry in candidate_files}
    all_paths = sorted(set(baseline_map) | set(candidate_map))

    changes: list[FileChange] = []
    for relative in all_paths:
        in_baseline = relative in baseline_map
        in_candidate = relative in candidate_map
        if in_baseline and in_candidate:
            if baseline_map[relative]["sha256"] == candidate_map[relative]["sha256"]:
                continue
            change_type = "modified"
        elif in_candidate:
            change_type = "added"
        else:
            change_type = "removed"

        old_side: str | None
        new_side: str | None
        if in_baseline:
            old_side = _read_text(baseline / relative)
        else:
            old_side = ""
        if in_candidate:
            new_side = _read_text(candidate / relative)
        else:
            new_side = ""

        if old_side is not None and new_side is not None:
            unified = "".join(
                difflib.unified_diff(
                    old_side.splitlines(keepends=True),
                    new_side.splitlines(keepends=True),
                    fromfile=f"baseline/{relative}",
                    tofile=f"candidate/{relative}",
                )
            )
            ranges = _changed_ranges(unified)
            text = True
        else:
            unified = (
                f"--- baseline/{relative}\n"
                f"+++ candidate/{relative}\n"
                f"(binary or undiffable change)\n"
            )
            ranges = ()
            text = False

        changes.append(
            FileChange(
                path=relative,
                change_type=change_type,
                unified_diff=unified,
                changed_ranges=ranges,
                text=text,
            )
        )

    return DiffCapture(
        baseline_dir=str(baseline),
        candidate_dir=str(candidate),
        baseline_id=baseline_id,
        candidate_id=candidate_id,
        baseline_files=baseline_files,
        candidate_files=candidate_files,
        changed_files=tuple(changes),
    )
