"""Expression values, normalization and reference extraction for HCL attributes.

Attribute raw source text is parsed into a small value tree so that
normalization and reference collection are deterministic instead of being
based on ad-hoc string matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Union

from .errors import HclSyntaxError
from .hcl import lex

_IDENT_START = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_IDENT_BODY = _IDENT_START | set("0123456789")


@dataclass(frozen=True)
class Str:
    value: str


@dataclass(frozen=True)
class Template:
    """String with interpolation; parts are ``str`` literals or value nodes."""

    parts: tuple


@dataclass(frozen=True)
class Num:
    raw: str


@dataclass(frozen=True)
class Bool:
    value: bool


@dataclass(frozen=True)
class Null:
    pass


@dataclass(frozen=True)
class ListVal:
    items: tuple


@dataclass(frozen=True)
class ObjectVal:
    entries: tuple  # tuple[(key, value)]

    def get(self, key: str):
        for entry_key, entry_value in self.entries:
            if entry_key == key:
                return entry_value
        return None


@dataclass(frozen=True)
class Ref:
    """Reference path, e.g. ``("aws_s3_bucket", "customer_data", "arn")``."""

    path: tuple


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple


@dataclass(frozen=True)
class Raw:
    """Uninterpreted expression text (operators, for-expressions, ...)."""

    text: str


Value = Union[Str, Template, Num, Bool, Null, ListVal, ObjectVal, Ref, Call, Raw]

_NULL = Null()
_RAW_REF_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_-]*)+")


class _ValueParser:
    def __init__(self, raw: str, file: str) -> None:
        self.raw = raw
        self.file = file
        self.tokens = [t for t in lex(raw, file) if t.kind != "NEWLINE"]
        self.index = 0

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def next(self):
        token = self.peek()
        if token is not None:
            self.index += 1
        return token

    def parse(self) -> Value:
        value = self.parse_value()
        token = self.peek()
        if token is not None and token.kind != "EOF":
            # Operators / for-expressions / anything unmodelled.
            return Raw(" ".join(self.raw.split()))
        return value

    def parse_value(self) -> Value:
        token = self.peek()
        if token is None or token.kind == "EOF":
            return Raw("")
        if token.kind == "STRING":
            self.next()
            return _string_value(token.value)
        if token.kind == "HEREDOC":
            self.next()
            return Str(token.value)
        if token.kind == "NUMBER":
            self.next()
            return Num(token.text)
        if token.kind == "SYMBOL" and token.text == "[":
            return self.parse_list()
        if token.kind == "SYMBOL" and token.text == "{":
            return self.parse_object()
        if token.kind == "IDENT":
            return self.parse_ident()
        self.next()
        return Raw(token.text)

    def parse_ident(self) -> Value:
        token = self.next()
        assert token is not None
        if token.text == "true":
            return Bool(True)
        if token.text == "false":
            return Bool(False)
        if token.text == "null":
            return _NULL
        path = [token.text]
        while True:
            token = self.peek()
            if token is None:
                break
            if token.kind == "SYMBOL" and token.text == ".":
                nxt = self.tokens[self.index + 1] if self.index + 1 < len(self.tokens) else None
                if nxt is None or nxt.kind not in ("IDENT", "STRING"):
                    break
                self.next()
                part = self.next()
                path.append(part.value if part.kind == "STRING" else part.text)
                continue
            if token.kind == "SYMBOL" and token.text == "[":
                self.next()
                inner = ""
                while True:
                    item = self.peek()
                    if item is None or item.kind == "EOF":
                        break
                    if item.kind == "SYMBOL" and item.text == "]":
                        self.next()
                        break
                    inner += item.text
                    self.next()
                path.append("[]")
                continue
            break
        if self.peek() is not None and self.peek().kind == "SYMBOL" and self.peek().text == "(":
            self.next()
            args = []
            while True:
                item = self.peek()
                if item is None or item.kind == "EOF":
                    break
                if item.kind == "SYMBOL" and item.text == ")":
                    self.next()
                    break
                if item.kind == "SYMBOL" and item.text in (",",):
                    self.next()
                    continue
                args.append(self.parse_value())
            return Call(".".join(path), tuple(args))
        return Ref(tuple(path))

    def parse_list(self) -> Value:
        self.next()  # '['
        items = []
        while True:
            token = self.peek()
            if token is None or token.kind == "EOF":
                raise HclSyntaxError("unterminated list", self.file)
            if token.kind == "SYMBOL" and token.text == "]":
                self.next()
                break
            if token.kind == "SYMBOL" and token.text == ",":
                self.next()
                continue
            items.append(self.parse_value())
        return ListVal(tuple(items))

    def parse_object(self) -> Value:
        self.next()  # '{'
        entries = []
        while True:
            token = self.peek()
            if token is None or token.kind == "EOF":
                raise HclSyntaxError("unterminated object", self.file)
            if token.kind == "SYMBOL" and token.text == "}":
                self.next()
                break
            if token.kind == "SYMBOL" and token.text in (",",):
                self.next()
                continue
            if token.kind not in ("IDENT", "STRING", "NUMBER"):
                return Raw(" ".join(self.raw.split()))
            key_token = self.next()
            key = key_token.value if key_token.kind == "STRING" else key_token.text
            equals = self.peek()
            if equals is None or equals.kind != "SYMBOL" or equals.text != "=":
                if equals is not None and equals.kind == "SYMBOL" and equals.text == ":":
                    self.next()
                else:
                    return Raw(" ".join(self.raw.split()))
            else:
                self.next()
            entries.append((key, self.parse_value()))
        return ObjectVal(tuple(entries))


def _string_value(text: str) -> Value:
    if "${" not in text:
        return Str(text)
    parts: list = []
    cursor = 0
    n = len(text)
    while cursor < n:
        start = text.find("${", cursor)
        if start < 0:
            if cursor < n:
                parts.append(text[cursor:])
            break
        if start > cursor:
            parts.append(text[cursor:start])
        depth = 1
        k = start + 2
        while k < n:
            if text[k] == "{":
                depth += 1
            elif text[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        inner = text[start + 2 : k]
        parts.append(parse_value(inner))
        cursor = k + 1
    if len(parts) == 1 and not isinstance(parts[0], str):
        return parts[0]
    return Template(tuple(parts))


def parse_value(raw: str, file: str = "<value>") -> Value:
    """Parse attribute raw text into a :class:`Value` tree."""
    stripped = raw.strip()
    if not stripped:
        return Raw("")
    try:
        return _ValueParser(raw, file).parse()
    except HclSyntaxError:
        return Raw(" ".join(stripped.split()))
    except RecursionError:
        return Raw(" ".join(stripped.split()))


def normalize(value: Value) -> tuple:
    """Deterministic, hashable normalization used for evidence comparison."""
    if isinstance(value, Str):
        return ("str", value.value)
    if isinstance(value, Template):
        parts = []
        for part in value.parts:
            if isinstance(part, str):
                parts.append(("lit", part))
            else:
                parts.append(normalize(part))
        return ("tmpl", tuple(parts))
    if isinstance(value, Num):
        return ("num", value.raw)
    if isinstance(value, Bool):
        return ("bool", value.value)
    if isinstance(value, Null):
        return ("null",)
    if isinstance(value, ListVal):
        return ("list", tuple(sorted((normalize(i) for i in value.items), key=repr)))
    if isinstance(value, ObjectVal):
        return (
            "obj",
            tuple(sorted((key, normalize(val)) for key, val in value.entries)),
        )
    if isinstance(value, Ref):
        return ("ref", value.path)
    if isinstance(value, Call):
        return ("call", value.name, tuple(sorted((normalize(a) for a in value.args), key=repr)))
    if isinstance(value, Raw):
        return ("raw", " ".join(value.text.split()))
    return ("raw", repr(value))


def flatten(value: Value, prefix: str = "", out: dict | None = None) -> dict:
    """Flatten a value tree into ``{path: leaf_repr}`` pairs for evidence."""
    if out is None:
        out = {}
    if isinstance(value, ObjectVal):
        for key, item in value.entries:
            flatten(item, f"{prefix}.{key}" if prefix else key, out)
        if not value.entries:
            out[prefix] = "{}"
        return out
    if isinstance(value, ListVal):
        if not value.items:
            out[prefix] = "[]"
        for index, item in enumerate(value.items):
            flatten(item, f"{prefix}[{index}]", out)
        return out
    out[prefix] = leaf_repr(value)
    return out


def leaf_repr(value: Value) -> str:
    """Short deterministic text for a leaf value (used in evidence details)."""
    norm = normalize(value)
    return _leaf_from_norm(norm)


def _leaf_from_norm(norm: tuple) -> str:
    kind = norm[0]
    if kind == "str":
        return str(norm[1])
    if kind == "ref":
        return "ref:" + ".".join(norm[1])
    if kind == "num":
        return str(norm[1])
    if kind == "bool":
        return "true" if norm[1] else "false"
    if kind == "null":
        return "null"
    if kind == "raw":
        return str(norm[1])
    if kind == "call":
        return f"call:{norm[1]}"
    if kind == "tmpl":
        rendered = []
        for part in norm[1]:
            rendered.append(part[1] if part[0] == "lit" else _leaf_from_norm(part))
        return "".join(rendered)
    if kind == "list":
        return "[" + ",".join(_leaf_from_norm(i) for i in norm[1]) + "]"
    if kind == "obj":
        return "{" + ",".join(f"{k}={_leaf_from_norm(v)}" for k, v in norm[1]) + "}"
    return repr(norm)


def literal_string(value: Value) -> str | None:
    """Return the literal string content, or None if not a literal."""
    if isinstance(value, Str):
        return value.value
    if isinstance(value, Template):
        out = []
        for part in value.parts:
            if isinstance(part, str):
                out.append(part)
            else:
                return None
        return "".join(out)
    return None


def iter_refs(value: Value) -> Iterator[Ref]:
    """Yield every :class:`Ref` reachable from a value tree."""
    if isinstance(value, Ref):
        yield value
    elif isinstance(value, Call):
        yield Ref(value.name.split("."))
        for arg in value.args:
            yield from iter_refs(arg)
    elif isinstance(value, ListVal):
        for item in value.items:
            yield from iter_refs(item)
    elif isinstance(value, ObjectVal):
        for _key, item in value.entries:
            yield from iter_refs(item)
    elif isinstance(value, Template):
        for part in value.parts:
            if not isinstance(part, str):
                yield from iter_refs(part)
    elif isinstance(value, Raw):
        for path in _raw_ref_paths(value.text):
            yield Ref(path)


def _raw_ref_paths(text: str) -> list:
    paths = []
    for match in _RAW_REF_RE.finditer(text):
        segments = [s.strip() for s in match.group(0).split(".")]
        cleaned = []
        for segment in segments:
            segment = re.sub(r"\[[^\]]*\]", "", segment)
            if segment:
                cleaned.append(segment)
        if cleaned:
            paths.append(tuple(cleaned))
    return paths


def ref_address(path: tuple, module_path: tuple = ()) -> str | None:
    """Qualify a reference path into a project address key.

    Returns None for references that do not denote a project node
    (``count``, ``each``, ``self``, ...).
    """
    if not path:
        return None
    head = path[0]
    prefix = "".join(f"module.{name}." for name in module_path)
    if head in ("count", "each", "self", "terraform", "path", "provider"):
        return None
    if head == "data":
        if len(path) < 3:
            return None
        return f"{prefix}data.{path[1]}.{path[2]}"
    if head in ("var", "local", "module", "output"):
        if len(path) < 2:
            return None
        return f"{prefix}{head}.{path[1]}"
    if len(path) < 2:
        return None
    return f"{prefix}{path[0]}.{path[1]}"


def ref_kind(path: tuple) -> str | None:
    """Category of a reference path (resource type, var, local, module, ...)."""
    if not path:
        return None
    head = path[0]
    if head == "data" and len(path) >= 3:
        return f"data.{path[1]}"
    if head in ("var", "local", "module", "output", "count", "each", "self", "terraform", "path", "provider"):
        return head
    if len(path) >= 2:
        return head
    return None
