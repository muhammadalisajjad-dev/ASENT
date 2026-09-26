"""P6 - security trigger discovery (deterministic static analysis).

Scans the resolved package source with :mod:`ast` for conditionals whose
predicate is security-sensitive (environment-variable checks, file-existence
checks, host/platform checks, or opaque calls that inline to those) and whose
branch reaches a sensitive sink (file read/write, network, process creation).

Output is a *trigger frontier* - a best-effort, explicitly non-exhaustive set
of conditions that CAVR can deliberately activate (or must report as
unexercisable).  Unsupported predicate shapes are classified as ``opaque``
and conservatively treated as not activatable.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from cavr.resolve import ResolvedPackage

RISK_HIGH = "high"
RISK_MEDIUM = "medium"

_HIGH_RISK_CONTROLS = (
    "canary-secret read path",
    "canary-sink write",
    "network connect",
    "process creation",
)


@dataclass(frozen=True)
class Trigger:
    """One discovered security-sensitive condition."""

    source_file: str
    line: int
    predicate: str
    predicate_kind: str
    controls: tuple[str, ...]
    risk: str
    activatable: bool
    activation: dict | None
    notes: str

    def as_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "line": self.line,
            "predicate": self.predicate,
            "predicate_kind": self.predicate_kind,
            "controls": list(self.controls),
            "risk": self.risk,
            "activatable": self.activatable,
            "activation": self.activation,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class TriggerReport:
    """Result of trigger discovery over one package."""

    scanned_files: tuple[str, ...]
    triggers: tuple[Trigger, ...]

    @property
    def unexercisable(self) -> tuple[Trigger, ...]:
        return tuple(t for t in self.triggers if not t.activatable)

    @property
    def activations(self) -> dict:
        """Merged activation environment for all activatable triggers."""
        env: dict[str, str] = {}
        files: list[str] = []
        for trigger in self.triggers:
            if not trigger.activatable or not trigger.activation:
                continue
            env.update(trigger.activation.get("env", {}))
            files.extend(trigger.activation.get("files", []))
        merged: dict = {}
        if env:
            merged["env"] = dict(sorted(env.items()))
        if files:
            merged["files"] = sorted(set(files))
        return merged

    def as_dict(self) -> dict:
        return {
            "scanned_files": list(self.scanned_files),
            "analyzer": "cavr_ast_trigger_discovery_v1",
            "exhaustiveness": "best-effort, not exhaustive",
            "triggers": [trigger.as_dict() for trigger in self.triggers],
        }


# ---- predicate analysis -------------------------------------------------


def _literal(node: ast.AST) -> object | None:
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _env_name_of(node: ast.AST) -> str | None:
    """`os.environ.get("X")` / `os.getenv("X")` -> "X"."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "get"
        and isinstance(func.value, ast.Attribute)
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "os"
        and func.value.attr == "environ"
    ):
        if node.args:
            value = _literal(node.args[0])
            if isinstance(value, str):
                return value
        return None
    if (
        isinstance(func, ast.Name)
        and func.id == "getenv"
        and node.args
        and isinstance(_literal(node.args[0]), str)
    ):
        return str(_literal(node.args[0]))
    return None


def _host_identity_of(node: ast.AST) -> str | None:
    """`platform.node()` / `socket.gethostname()` -> display string."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr == "node" and isinstance(func.value, ast.Name) and func.value.id == "platform":
            return "platform.node()"
        if func.attr == "gethostname" and isinstance(func.value, ast.Name) and func.value.id == "socket":
            return "socket.gethostname()"
    if isinstance(func, ast.Name) and func.id == "gethostname":
        return "gethostname()"
    return None


def _exists_call(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in ("exists", "is_file", "is_dir"):
        target = None
        if func.attr == "exists" and isinstance(func.value, ast.Attribute):
            # os.path.exists(...)
            if isinstance(func.value.value, ast.Name) and func.value.value.id == "os":
                target = _first_arg_string(node)
        elif isinstance(func.value, ast.Call):
            # Path(...).exists()
            target = _first_arg_string(func.value)
        if target:
            return f"{target} {func.attr}"
        return f"<path>.{func.attr}"
    return None


def _first_arg_string(node: ast.Call) -> str | None:
    if node.args:
        value = _literal(node.args[0])
        if isinstance(value, str):
            return value
    return None


def _is_environ_contains(node: ast.AST) -> str | None:
    """`"X" in os.environ` -> "X"."""
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return None
    if not isinstance(node.ops[0], ast.In):
        return None
    right = node.comparators[0]
    if (
        isinstance(right, ast.Attribute)
        and right.attr == "environ"
        and isinstance(right.value, ast.Name)
        and right.value.id == "os"
    ):
        value = _literal(node.left)
        if isinstance(value, str):
            return value
    return None


def _env_names_in(node: ast.AST) -> list[str]:
    names: list[str] = []
    for child in ast.walk(node):
        name = _env_name_of(child)
        if name:
            names.append(name)
        contains = _is_environ_contains(child)
        if contains:
            names.append(contains)
    return sorted(set(names))


def _markers_in(node: ast.AST) -> set[str]:
    """Classify security-relevant markers appearing anywhere under *node*."""
    markers: set[str] = set()
    if _env_names_in(node):
        markers.add("env_var")
    for child in ast.walk(node):
        if _host_identity_of(child):
            markers.add("host_identity")
        if _exists_call(child):
            markers.add("file_exists")
        if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
            if child.value.id == "platform" and child.attr in (
                "system",
                "machine",
                "release",
            ):
                markers.add("platform")
            if child.value.id == "sys" and child.attr == "platform":
                markers.add("platform")
    return markers


def _describe_test(
    test: ast.AST, module_functions: dict[str, ast.FunctionDef]
) -> dict:
    """Describe a branch predicate: kind, activation, activatability."""
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        left, op, right = test.left, test.ops[0], test.comparators[0]
        if isinstance(left, ast.Name) and left.id == "__name__":
            return {
                "predicate": "__name__ == __main__",
                "predicate_kind": "entrypoint",
                "activatable": False,
                "activation": None,
                "notes": "module entrypoint guard, not a security condition",
                "skip": True,
            }
        env_name = _env_name_of(left)
        env_value = _literal(right)
        if env_name and isinstance(env_value, str) and isinstance(op, ast.Eq):
            return {
                "predicate": f"{env_name} == {env_value}",
                "predicate_kind": "env_var",
                "activatable": True,
                "activation": {"env": {env_name: env_value}},
                "notes": "environment-variable condition; activated via sandbox env",
                "skip": False,
            }
        if env_name and isinstance(env_value, str) and isinstance(op, ast.NotEq):
            return {
                "predicate": f"{env_name} != {env_value}",
                "predicate_kind": "env_var",
                "activatable": False,
                "activation": None,
                "notes": "negated environment condition not exercised by this slice",
                "skip": False,
            }
        host = _host_identity_of(left) or _host_identity_of(right)
        if host:
            wanted = _literal(right) if _host_identity_of(left) else _literal(left)
            return {
                "predicate": f"{host} == {wanted!r}" if isinstance(wanted, str) else host,
                "predicate_kind": "host_identity",
                "activatable": False,
                "activation": None,
                "notes": "host-identity predicate cannot be safely exercised by CAVR",
                "skip": False,
            }
        if (
            isinstance(left, ast.Attribute)
            and left.attr == "platform"
            and isinstance(left.value, ast.Name)
            and left.value.id == "sys"
        ):
            return {
                "predicate": f"sys.platform == {_literal(right)!r}",
                "predicate_kind": "platform",
                "activatable": False,
                "activation": None,
                "notes": "platform predicate not exercised by this slice",
                "skip": False,
            }

    contains_name = _is_environ_contains(test)
    if contains_name:
        return {
            "predicate": f"{contains_name} present",
            "predicate_kind": "env_var",
            "activatable": True,
            "activation": {"env": {contains_name: "1"}},
            "notes": "environment-variable presence check; activated via sandbox env",
            "skip": False,
        }

    exists_display = _exists_call(test)
    if exists_display:
        return {
            "predicate": exists_display,
            "predicate_kind": "file_exists",
            "activatable": "<path>" not in exists_display,
            "activation": {"files": [exists_display.split()[0]]}
            if "<path>" not in exists_display
            else None,
            "notes": "file-existence condition; activated by planting the file",
            "skip": False,
        }

    if isinstance(test, ast.Call) and isinstance(test.func, ast.Name):
        func_def = module_functions.get(test.func.id)
        if func_def is not None:
            markers = _markers_in(func_def)
            if "host_identity" in markers:
                return {
                    "predicate": f"{test.func.id}() [host-identity gate]",
                    "predicate_kind": "host_identity",
                    "activatable": False,
                    "activation": None,
                    "notes": (
                        f"inlined {test.func.id}() depends on host identity; "
                        "cannot be safely exercised by CAVR"
                    ),
                    "skip": False,
                }
            if "env_var" in markers:
                names = _env_names_in(func_def)
                if len(names) == 1:
                    return {
                        "predicate": f"{test.func.id}() [env gate: {names[0]}]",
                        "predicate_kind": "env_var",
                        "activatable": True,
                        "activation": {"env": {names[0]: "1"}},
                        "notes": f"inlined {test.func.id}() environment gate",
                        "skip": False,
                    }
                return {
                    "predicate": f"{test.func.id}() [env gate: {', '.join(names)}]",
                    "predicate_kind": "env_var",
                    "activatable": False,
                    "activation": None,
                    "notes": "multi-variable gate not exercised by this slice",
                    "skip": False,
                }
            if "platform" in markers:
                return {
                    "predicate": f"{test.func.id}() [platform gate]",
                    "predicate_kind": "platform",
                    "activatable": False,
                    "activation": None,
                    "notes": f"inlined {test.func.id}() depends on platform",
                    "skip": False,
                }
            if "file_exists" in markers:
                return {
                    "predicate": f"{test.func.id}() [file-existence gate]",
                    "predicate_kind": "file_exists",
                    "activatable": False,
                    "activation": None,
                    "notes": f"inlined {test.func.id}() file gate not resolvable to a literal path",
                    "skip": False,
                }
            return {
                "predicate": f"{test.func.id}()",
                "predicate_kind": "opaque",
                "activatable": False,
                "activation": None,
                "notes": f"inlined {test.func.id}() has no recognized gate marker",
                "skip": False,
            }

    return {
        "predicate": _unparse(test),
        "predicate_kind": "opaque",
        "activatable": False,
        "activation": None,
        "notes": "predicate shape outside the supported trigger families",
        "skip": False,
    }


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - unparse available on 3.9+
        return "<unparsed>"


# ---- sink analysis ------------------------------------------------------

_READ_ATTRS = ("read_text", "read_bytes")
_WRITE_ATTRS = ("write_text", "write_bytes", "writelines")
_NETWORK_ATTRS = ("connect", "sendto", "urlopen", "getaddrinfo")
_PROCESS_ATTRS = (
    "run",
    "Popen",
    "call",
    "check_call",
    "check_output",
    "system",
    "popen",
    "spawnl",
    "spawnv",
    "execl",
    "execv",
)
_PROCESS_NAMES = ("exec", "execv", "execl", "system", "popen", "spawnl", "spawnv")


def _classify_call(node: ast.Call) -> list[dict]:
    """Classify one call expression into zero or more sink records."""
    sinks: list[dict] = []
    func = node.func

    if isinstance(func, ast.Name):
        if func.id == "open":
            mode = "r"
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value)
            if any(flag in mode for flag in ("w", "a", "x", "+")):
                sinks.append({"kind": "file_write", "target": _first_arg_string(node)})
            else:
                sinks.append({"kind": "file_read", "target": _first_arg_string(node)})
        elif func.id in _PROCESS_NAMES:
            sinks.append({"kind": "process_create", "target": func.id})
        return sinks

    if not isinstance(func, ast.Attribute):
        return sinks

    owner = func.value
    owner_name = owner.id if isinstance(owner, ast.Name) else None
    attr = func.attr

    if attr in _READ_ATTRS:
        sinks.append({"kind": "file_read", "target": _first_arg_string(node)})
    elif attr in _WRITE_ATTRS:
        sinks.append({"kind": "file_write", "target": _first_arg_string(node)})
    elif attr in _NETWORK_ATTRS and (
        owner_name in ("socket", "urllib_request", "requests", "urllib") or owner_name is None
    ):
        sinks.append({"kind": "network_connect", "target": attr})
    elif attr in _PROCESS_ATTRS and owner_name in ("subprocess", "os"):
        sinks.append({"kind": "process_create", "target": f"{owner_name}.{attr}"})
    elif owner_name == "shutil" and attr.startswith("copy"):
        sinks.append({"kind": "file_write", "target": "shutil.copy"})
    return sinks


def _describe_controls(sinks: list[dict], literals: str) -> tuple[str, ...]:
    labels: list[str] = []
    canary = "canary" in literals or "secret" in literals
    sink_marker = "sink" in literals
    for sink in sinks:
        if sink["kind"] == "file_read":
            label = "canary-secret read path" if canary else "file read"
        elif sink["kind"] == "file_write":
            label = "canary-sink write" if (sink_marker or canary) else "file write"
        elif sink["kind"] == "network_connect":
            label = "network connect"
        else:
            label = "process creation"
        if label not in labels:
            labels.append(label)
    return tuple(labels)


def _branch_sinks(bodies: list[ast.stmt]) -> tuple[list[dict], str]:
    """Collect sensitive sinks and literal strings from branch bodies."""
    sinks: list[dict] = []
    literals: list[str] = []
    for body in bodies:
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                literals.append(node.value.lower())
            if isinstance(node, ast.Call):
                sinks.extend(_classify_call(node))
    return sinks, " ".join(literals)


def discover_triggers(resolved: ResolvedPackage) -> TriggerReport:
    """Discover security-sensitive conditions in the resolved package."""
    root = Path(resolved.source_dir)
    scanned: list[str] = []
    found: list[Trigger] = []

    source_files = sorted(
        (
            path
            for path in root.rglob("*.py")
            if not {"__pycache__", ".git"} & set(path.relative_to(root).parts)
        ),
        key=lambda p: p.relative_to(root).as_posix(),
    )

    for path in source_files:
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        scanned.append(relative)

        module_functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            info = _describe_test(node.test, module_functions)
            if info.get("skip"):
                continue
            sinks, literals = _branch_sinks(list(node.body) + list(node.orelse))
            if not sinks:
                # A condition with no sensitive sink is not a trigger frontier
                # entry for this slice.
                continue
            controls = _describe_controls(sinks, literals)
            if not controls:
                continue
            risk = RISK_HIGH if any(c in _HIGH_RISK_CONTROLS for c in controls) else RISK_MEDIUM
            found.append(
                Trigger(
                    source_file=relative,
                    line=node.lineno,
                    predicate=str(info["predicate"]),
                    predicate_kind=str(info["predicate_kind"]),
                    controls=controls,
                    risk=risk,
                    activatable=bool(info["activatable"]),
                    activation=info["activation"],
                    notes=str(info["notes"]),
                )
            )

    found.sort(key=lambda t: (t.source_file, t.line, t.predicate))
    return TriggerReport(scanned_files=tuple(scanned), triggers=tuple(found))
