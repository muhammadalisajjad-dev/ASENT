"""M2 - security-change localizer (deterministic, bounded).

Maps the changed regions produced by M1 onto security-sensitive code
structure in a Flask application: route decorators, authentication signals,
authorization/ownership checks, resource lookups and identity comparisons.
The output is a structured security-region record (file, line range,
function/route, security family, mapping reason, confidence).

This is deliberately a bounded static heuristic, NOT complete program
analysis; exhaustiveness is reported as uncertainty, never claimed.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from satra_rv.capture import DiffCapture, FileChange

FAMILY_AUTHORIZATION = "authorization_ownership"

ROUTE_ATTRS = {"route", "get", "post", "put", "patch", "delete"}
OWNER_ATTRS = frozenset({"owner", "owner_id", "user_id", "created_by", "assigned_to", "user"})
ABORT_AUTHZ_CODES = (401, 403)
_REMOVED_SECURITY_MARKERS = (
    "abort(401",
    "abort(403",
    '["owner"]',
    ".owner",
    "login_required",
    "current_user",
    "_authorize",
)


@dataclass(frozen=True)
class RouteInfo:
    """A Flask route decorator found on a function."""

    decorator: str
    path: str
    method: str


@dataclass(frozen=True)
class SecurityRegion:
    """A changed region mapped to a security concern."""

    file: str
    start_line: int
    end_line: int
    function: str | None
    route: str | None
    method: str | None
    security_family: str
    mapping_reason: str
    confidence: float
    confidence_label: str
    signals: tuple[str, ...]
    changed_lines: tuple[int, ...]

    @property
    def affected_functions(self) -> tuple[str, ...]:
        return (self.function,) if self.function else ()

    def as_dict(self) -> dict:
        return {
            "file": self.file,
            "line_range": [self.start_line, self.end_line],
            "function": self.function,
            "route": self.route,
            "method": self.method,
            "security_family": self.security_family,
            "mapping_reason": self.mapping_reason,
            "confidence": self.confidence,
            "confidence_label": self.confidence_label,
            "signals": list(self.signals),
            "changed_lines": list(self.changed_lines),
        }


@dataclass(frozen=True)
class LocalizationResult:
    """M2 output: security regions localized from the change set."""

    regions: tuple[SecurityRegion, ...]
    scanned_files: tuple[str, ...]
    notes: tuple[str, ...]

    @property
    def primary(self) -> SecurityRegion | None:
        """Best region for contract binding: prefers route-bearing regions.

        The Security Change Contract binds dictionary invariants by Flask
        route, so a region that names a route is more actionable than a
        higher-scoring helper region that does not.
        """
        if not self.regions:
            return None
        return max(
            self.regions,
            key=lambda r: (bool(r.route), r.confidence, -r.start_line),
        )

    @property
    def families(self) -> tuple[str, ...]:
        return tuple(sorted({region.security_family for region in self.regions}))

    def as_dict(self) -> dict:
        return {
            "analyzer": "satra_rv_security_localizer_v1",
            "bounded": "deterministic static heuristic, not complete program analysis",
            "scanned_files": list(self.scanned_files),
            "notes": list(self.notes),
            "regions": [region.as_dict() for region in self.regions],
            "primary": self.primary.as_dict() if self.primary else None,
        }


# ---- AST signal extraction ----------------------------------------------


def _walk_own(node: ast.AST):
    """Walk ``node`` without descending into functions nested inside it.

    Flask route handlers are commonly nested inside a ``create_app``
    factory; signals must be attributed to the function that actually
    contains them, not to every enclosing scope.
    """
    stack = list(ast.iter_child_nodes(node))
    while stack:
        current = stack.pop()
        yield current
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        stack.extend(ast.iter_child_nodes(current))


def _decorator_node(decorator: ast.expr) -> ast.expr:
    return decorator.func if isinstance(decorator, ast.Call) else decorator


def _route_of(decorator: ast.expr) -> RouteInfo | None:
    node = _decorator_node(decorator)
    if not isinstance(node, ast.Attribute) or node.attr not in ROUTE_ATTRS:
        return None
    args = decorator.args if isinstance(decorator, ast.Call) else []
    if not args or not isinstance(args[0], ast.Constant) or not isinstance(args[0].value, str):
        return None
    path = args[0].value
    method = node.attr.upper() if node.attr != "route" else "GET"
    if isinstance(decorator, ast.Call):
        for keyword in decorator.keywords:
            if keyword.arg == "methods" and isinstance(keyword.value, ast.List):
                for element in keyword.value.elts:
                    if isinstance(element, ast.Constant) and isinstance(element.value, str):
                        method = element.value.upper()
                        break
    return RouteInfo(decorator=node.attr, path=path, method=method)


def _is_auth_decorator(decorator: ast.expr) -> bool:
    node = _decorator_node(decorator)
    if isinstance(node, ast.Name):
        name = node.id
    elif isinstance(node, ast.Attribute):
        name = node.attr
    else:
        return False
    return name.endswith("_required") or name.endswith("_required_user")


def _string_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_owner_operand(node: ast.expr) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr in OWNER_ATTRS
    if isinstance(node, ast.Subscript):
        key = _string_key(node.slice)
        return key is not None and key in OWNER_ATTRS
    return False


def _is_identity_operand(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return "user" in node.id.lower() or node.id.lower() in {"me", "principal"}
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id in {
            "current_user",
            "session",
            "g",
        }:
            return True
        if node.attr in {"id", "user_id"} and isinstance(node.value, ast.Name):
            return "user" in node.value.id.lower() or node.value.id == "current_user"
        return False
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            low = node.func.id.lower()
            return "user" in low or "auth" in low or "principal" in low
        if isinstance(node.func, ast.Attribute):
            if "user" in node.func.attr.lower() or "auth" in node.func.attr.lower():
                return True
            receiver = node.func.value
            if (
                isinstance(receiver, ast.Attribute)
                and isinstance(receiver.value, ast.Name)
                and receiver.value.id == "request"
            ):
                return True
        return False
    if isinstance(node, ast.Subscript):
        base = node.value
        if isinstance(base, ast.Name) and base.id in {"session", "g"}:
            return True
        key = _string_key(node.slice)
        return key is not None and "user" in key.lower()
    return False


def _ownership_comparisons(node: ast.AST) -> list[ast.Compare]:
    matches = []
    for child in _walk_own(node):
        if isinstance(child, ast.Compare) and len(child.ops) == 1:
            left, right = child.left, child.comparators[0]
            if (_is_owner_operand(left) and _is_identity_operand(right)) or (
                _is_identity_operand(left) and _is_owner_operand(right)
            ):
                matches.append(child)
    return matches


def _identity_assignments(node: ast.AST) -> list[str]:
    found = []
    for child in _walk_own(node):
        if isinstance(child, ast.Assign):
            for target in child.targets:
                if (
                    isinstance(target, ast.Name)
                    and "user" in target.id.lower()
                    and isinstance(child.value, (ast.Call, ast.Subscript, ast.Attribute))
                ):
                    found.append(target.id)
    return found


def _resource_lookups(node: ast.AST) -> list[str]:
    found = []
    for child in _walk_own(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            attr = child.func.attr
            receiver = child.func.value
            if attr in {"get", "get_or_404", "first_or_404"}:
                if isinstance(receiver, ast.Name) and (
                    receiver.id.isupper()
                    or "invoice" in receiver.id.lower()
                    or "resource" in receiver.id.lower()
                ):
                    found.append(f"{receiver.id}.{attr}()")
                elif isinstance(receiver, ast.Attribute) and receiver.attr in {
                    "query",
                    "session",
                }:
                    found.append(f"query.{attr}()")
        if (
            isinstance(child, ast.Subscript)
            and isinstance(child.value, ast.Name)
            and child.value.id.isupper()
        ):
            found.append(f"{child.value.id}[...]")
    return sorted(set(found))


def _abort_codes(node: ast.AST) -> list[int]:
    codes = []
    for child in _walk_own(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "abort"
            and child.args
            and isinstance(child.args[0], ast.Constant)
            and isinstance(child.args[0].value, int)
        ):
            codes.append(child.args[0].value)
    return codes


def _authz_helper_calls(node: ast.AST) -> list[str]:
    names = []
    for child in _walk_own(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            low = child.func.id.lower()
            if low.startswith("_") and any(
                keyword in low
                for keyword in ("authorize", "require", "permission", "access")
            ):
                names.append(child.func.id)
    return sorted(set(names))


def _removed_security_lines(change: FileChange) -> tuple[str, ...]:
    removed = []
    for line in change.unified_diff.splitlines():
        if line.startswith("---") or not line.startswith("-"):
            continue
        text = line[1:]
        if any(marker in text for marker in _REMOVED_SECURITY_MARKERS):
            removed.append(text.strip())
    return tuple(removed)


def _confidence_label(score: float) -> str:
    if score >= 0.70:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


# ---- localization ---------------------------------------------------------


def _analyze_function(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    file_change: FileChange,
    changed_lines: set[int],
    removed_signals: tuple[str, ...],
) -> SecurityRegion | None:
    routes = [route for dec in func.decorator_list if (route := _route_of(dec))]
    auth_decorators = [dec for dec in func.decorator_list if _is_auth_decorator(dec)]
    comparisons = _ownership_comparisons(func)
    identity = _identity_assignments(func)
    lookups = _resource_lookups(func)
    aborts = [code for code in _abort_codes(func) if code in ABORT_AUTHZ_CODES]
    helpers = _authz_helper_calls(func)

    signals: list[str] = []
    if routes:
        signals.append(f"route {routes[0].method} {routes[0].path}")
    if auth_decorators:
        signals.append("authentication decorator")
    if comparisons:
        signals.append("ownership comparison (resource owner vs current user)")
    if identity:
        signals.append(f"identity assignment ({', '.join(sorted(set(identity)))})")
    if lookups:
        signals.append(f"resource lookup ({', '.join(lookups)})")
    if aborts:
        signals.append(f"authorization abort {sorted(set(aborts))}")
    if helpers:
        signals.append(f"authorization helper call ({', '.join(helpers)})")
    if removed_signals:
        signals.append(
            f"security-relevant line(s) removed by change: {removed_signals[0]!r}"
        )

    is_security_family = bool(comparisons) or bool(helpers) or bool(auth_decorators) or (
        bool(routes) and (bool(aborts) or bool(identity))
    )
    if not is_security_family and not (removed_signals and (routes or lookups)):
        return None

    score = 0.0
    if routes:
        score += 0.35
    if comparisons:
        score += 0.25
    if aborts:
        score += 0.15
    if auth_decorators:
        score += 0.10
    if lookups:
        score += 0.10
    if identity:
        score += 0.10
    if helpers:
        score += 0.05
    if removed_signals:
        score += 0.10
    score = min(score, 0.95)

    overlapping = sorted(line for line in changed_lines if func.lineno <= line <= (func.end_lineno or func.lineno))
    route = routes[0] if routes else None

    parts = [
        f"changed lines {overlapping[0]}-{overlapping[-1]}"
        if overlapping
        else f"function lines {func.lineno}-{func.end_lineno}"
        f" overlap changed region"
    ]
    if func is not None:
        parts = [f"changed lines overlap {func.name}()"] + parts[1:]
    if route:
        parts.append(f"route {route.method} {route.path}")
    parts.append("signals: " + ", ".join(signals) if signals else "no signals")

    return SecurityRegion(
        file=file_change.path,
        start_line=func.lineno,
        end_line=func.end_lineno or func.lineno,
        function=func.name,
        route=route.path if route else None,
        method=route.method if route else None,
        security_family=FAMILY_AUTHORIZATION,
        mapping_reason="; ".join(parts),
        confidence=round(score, 2),
        confidence_label=_confidence_label(score),
        signals=tuple(signals),
        changed_lines=tuple(overlapping),
    )


def localize(diff: DiffCapture) -> LocalizationResult:
    """Localize security-sensitive changed regions from the diff (M2)."""
    regions: list[SecurityRegion] = []
    scanned: list[str] = []
    notes: list[str] = []

    for change in diff.changed_files:
        if not change.path.endswith(".py"):
            continue
        candidate_path = Path(diff.candidate_dir) / change.path
        if not candidate_path.is_file():
            notes.append(f"{change.path}: removed in candidate; not localizable")
            continue
        try:
            tree = ast.parse(candidate_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            notes.append(f"{change.path}: candidate not parseable ({exc})")
            continue
        scanned.append(change.path)

        removed_signals = _removed_security_lines(change)
        changed_lines = set(change.changed_line_numbers)

        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        functions.sort(key=lambda node: node.lineno)
        matched_any = False
        for func in functions:
            span = range(func.lineno, (func.end_lineno or func.lineno) + 1)
            if not (changed_lines & set(span)):
                continue
            region = _analyze_function(func, change, changed_lines, removed_signals)
            if region is not None:
                regions.append(region)
                matched_any = True

        if removed_signals and not matched_any:
            notes.append(
                f"{change.path}: security-relevant lines changed outside any "
                "localized function"
            )

    regions.sort(
        key=lambda r: (r.file, r.start_line, -r.confidence)
    )
    return LocalizationResult(
        regions=tuple(regions), scanned_files=tuple(scanned), notes=tuple(notes)
    )
