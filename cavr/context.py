"""P3 - minimal project context.

Extracts just enough local, deterministic context to justify the expected
behavior of a dependency: declared feature intent (README/task file),
requirements file entries, and import statements of the small project source
fixture.  No inference beyond explicit declarations; no LLM.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from shared.errors import InputError

INTENT_FILES = ("README.md", "README.txt", "TASK.md", "intent.txt")


@dataclass(frozen=True)
class ProjectContext:
    """Local project context used to derive the capability contract."""

    project_dir: str
    intent: str
    intent_source: str
    requirements: tuple[str, ...]
    imports: tuple[str, ...]
    runtime_input_dirs: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "project_dir": self.project_dir,
            "intent": self.intent,
            "intent_source": self.intent_source,
            "requirements": list(self.requirements),
            "imports": list(self.imports),
            "runtime_input_dirs": list(self.runtime_input_dirs),
        }


def _read_intent(project_dir: Path) -> tuple[str, str]:
    for name in INTENT_FILES:
        candidate = project_dir / name
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text, name
    raise InputError(
        f"no intent declaration found in {project_dir} "
        f"(expected one of {INTENT_FILES})"
    )


def _read_requirements(project_dir: Path) -> tuple[str, ...]:
    requirements_path = project_dir / "requirements.txt"
    if not requirements_path.is_file():
        return ()
    entries = []
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return tuple(entries)


def _collect_imports(project_dir: Path) -> tuple[str, ...]:
    modules: set[str] = set()
    for source in sorted(project_dir.rglob("*.py")):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return tuple(sorted(modules))


def load_context(project_dir: str | Path) -> ProjectContext:
    """Load deterministic local context for the requesting project."""
    root = Path(project_dir)
    if not root.is_dir():
        raise InputError(f"project directory not found: {root}")
    intent, intent_source = _read_intent(root)
    runtime_inputs = tuple(
        sorted(
            path.name
            for path in root.iterdir()
            if path.is_dir() and path.name == "input"
        )
    )
    return ProjectContext(
        project_dir=str(root),
        intent=intent,
        intent_source=intent_source,
        requirements=_read_requirements(root),
        imports=_collect_imports(root),
        runtime_input_dirs=runtime_inputs,
    )
