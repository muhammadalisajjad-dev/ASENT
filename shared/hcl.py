"""Minimal HCL2 lexer/parser covering the Terraform subset SABLE needs.

Only block/attribute structure with source positions is produced.  Expression
bodies are kept as raw source text and are interpreted later by
:mod:`shared.values`.  Anything that cannot be parsed raises
:class:`~shared.errors.HclSyntaxError` instead of being guessed at.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Union

from .errors import HclSyntaxError

_IDENT_START = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_IDENT_BODY = _IDENT_START | set("0123456789")
_DIGITS = set("0123456789")
_SINGLE_SYMBOLS = set("{}[](),=.:")
_OPERATOR_CHARS = set("+-*/%<>!&|?:")
_STRING_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    '"': '"',
    "\\": "\\",
    "'": "'",
    "0": "\0",
    "u": None,
}


@dataclass(frozen=True)
class Position:
    """A source location inside a Terraform file."""

    file: str
    line: int
    column: int
    offset: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"


@dataclass(frozen=True)
class Attribute:
    """``name = <expression>`` with the expression kept as raw source text."""

    name: str
    raw: str
    position: Position


@dataclass(frozen=True)
class Block:
    """A labelled HCL block such as ``resource "aws_s3_bucket" "data" { ... }``."""

    type: str
    labels: tuple
    body: tuple
    position: Position

    def attributes(self) -> list:
        return [item for item in self.body if isinstance(item, Attribute)]

    def get_attribute(self, name: str) -> Attribute | None:
        for item in self.body:
            if isinstance(item, Attribute) and item.name == name:
                return item
        return None

    def nested(self, block_type: str | None = None) -> list:
        blocks = [item for item in self.body if isinstance(item, Block)]
        if block_type is None:
            return blocks
        return [block for block in blocks if block.type == block_type]

    def walk(self) -> Iterator:
        """Yield this block and every nested block."""
        yield self
        for item in self.body:
            if isinstance(item, Block):
                yield from item.walk()


Item = Union[Attribute, Block]


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    value: str
    start: int
    end: int
    line: int
    column: int


def _position(token: Token, file: str) -> Position:
    return Position(file=file, line=token.line, column=token.column, offset=token.start)


def lex(source: str, file: str = "<string>") -> list:
    """Tokenize HCL source into a list of :class:`Token` (newline-sensitive)."""
    tokens: list = []
    i = 0
    line = 1
    column = 1
    n = len(source)

    def add(kind: str, start: int, end: int, value: str, tok_line: int, tok_col: int) -> None:
        tokens.append(
            Token(
                kind=kind,
                text=source[start:end],
                value=value,
                start=start,
                end=end,
                line=tok_line,
                column=tok_col,
            )
        )

    while i < n:
        ch = source[i]
        if ch in " \t":
            i += 1
            column += 1
            continue
        if ch == "\r" or ch == "\n":
            start = i
            start_line, start_col = line, column
            if ch == "\r" and i + 1 < n and source[i + 1] == "\n":
                i += 2
            else:
                i += 1
            line += 1
            column = 1
            add("NEWLINE", start, i, "\n", start_line, start_col)
            continue
        if ch == "#" or (ch == "/" and i + 1 < n and source[i + 1] == "/"):
            while i < n and source[i] not in "\r\n":
                i += 1
                column += 1
            continue
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            i += 2
            column += 2
            while i < n and not (source[i] == "*" and i + 1 < n and source[i + 1] == "/"):
                if source[i] == "\n":
                    line += 1
                    column = 1
                else:
                    column += 1
                i += 1
            i += 2
            column += 2
            continue

        start = i
        start_line, start_col = line, column

        if ch == '"':
            value, i, column = _read_string(source, i, column)
            add("STRING", start, i, value, start_line, start_col)
            continue

        if ch == "<" and source.startswith("<<", i):
            heredoc = _read_heredoc(source, i)
            if heredoc is not None:
                value, end = heredoc
                consumed = source[start:end]
                line += consumed.count("\n")
                last_newline = consumed.rfind("\n")
                if last_newline >= 0:
                    column = len(consumed) - last_newline
                else:
                    column += len(consumed)
                i = end
                add("HEREDOC", start, i, value, start_line, start_col)
                continue

        if ch in _IDENT_START:
            j = i + 1
            while j < n and source[j] in _IDENT_BODY:
                j += 1
            column += j - i
            add("IDENT", i, j, source[i:j], start_line, start_col)
            i = j
            continue

        if ch in _DIGITS or (ch == "." and i + 1 < n and source[i + 1] in _DIGITS):
            j = i
            while j < n and (
                source[j] in _DIGITS
                or source[j] in ".eE"
                or (source[j] in "+-" and j > i and source[j - 1] in "eE")
            ):
                j += 1
            column += j - i
            add("NUMBER", i, j, source[i:j], start_line, start_col)
            i = j
            continue

        if ch in _SINGLE_SYMBOLS:
            column += 1
            add("SYMBOL", i, i + 1, ch, start_line, start_col)
            i += 1
            continue

        if ch in _OPERATOR_CHARS:
            two = source[i : i + 2]
            if two in ("==", "!=", "<=", ">=", "&&", "||", "=>", "..."):
                column += 2
                add("OP", i, i + 2, two, start_line, start_col)
                i += 2
                continue
            column += 1
            add("OP", i, i + 1, ch, start_line, start_col)
            i += 1
            continue

        raise HclSyntaxError(
            f"unexpected character {ch!r}",
            Position(file=file, line=line, column=column, offset=i),
        )

    tokens.append(Token("EOF", "", "", n, n, line, column))
    return tokens


def _read_string(source: str, i: int, column: int) -> tuple:
    """Read a quoted string starting at ``source[i] == '"'``.

    Returns ``(decoded_value, next_index, next_column)``.  Interpolation
    sequences ``${...}`` are preserved verbatim inside the value.
    """
    n = len(source)
    j = i + 1
    column += 1
    out: list = []
    while j < n:
        ch = source[j]
        if ch == "\\":
            if j + 1 >= n:
                break
            nxt = source[j + 1]
            if nxt == "u":
                hex_digits = source[j + 2 : j + 6]
                out.append(chr(int(hex_digits, 16)))
                j += 6
                column += 6
                continue
            out.append(_STRING_ESCAPES.get(nxt, nxt))
            j += 2
            column += 2
            continue
        if ch == '"':
            j += 1
            column += 1
            return "".join(out), j, column
        if ch == "$" and source.startswith("${", j):
            depth = 1
            k = j + 2
            while k < n:
                c = source[k]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
                elif c == '"':
                    k += 1
                    while k < n and source[k] != '"':
                        if source[k] == "\\":
                            k += 1
                        k += 1
                k += 1
            out.append(source[j : k + 1])
            column += k + 1 - j
            j = k + 1
            continue
        if ch == "\n":
            raise HclSyntaxError("unterminated string literal")
        out.append(ch)
        j += 1
        column += 1
    raise HclSyntaxError("unterminated string literal")


def _read_heredoc(source: str, i: int) -> tuple | None:
    """Read ``<<MARKER``/``<<-MARKER`` heredocs; returns None if not one."""
    match = re.match(r"<<-?([A-Za-z_][A-Za-z0-9_]*)[ \t]*\r?\n", source[i:])
    if match is None:
        return None
    marker = match.group(1)
    body_start = i + match.end()
    terminator = re.search(
        r"^[ \t]*" + re.escape(marker) + r"[ \t]*$", source[body_start:], re.MULTILINE
    )
    if terminator is None:
        raise HclSyntaxError("unterminated heredoc")
    body_end = body_start + terminator.start()
    value = source[body_start:body_end]
    end = body_start + terminator.end()
    return value, end


def parse_string(source: str, file: str = "<string>") -> list:
    """Parse HCL source into top-level :class:`Attribute`/:class:`Block` items."""
    tokens = lex(source, file)
    items, index = _parse_body(tokens, 0, source, file, top_level=True)
    return items


def parse_file(path: str | Path) -> list:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HclSyntaxError(f"cannot read {path}: {exc}") from exc
    return parse_string(text, file=str(path))


def parse_directory(path: str | Path) -> dict:
    """Parse every ``*.tf`` file in a directory (sorted by name)."""
    directory = Path(path)
    if not directory.is_dir():
        raise HclSyntaxError(f"not a directory: {directory}")
    result: dict = {}
    for file in sorted(directory.glob("*.tf")):
        result[file.name] = parse_file(file)
    return result


def _parse_body(
    tokens: list,
    index: int,
    source: str,
    file: str,
    top_level: bool,
    open_token: Token | None = None,
) -> tuple:
    items: list = []
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "NEWLINE":
            index += 1
            continue
        if token.kind == "EOF":
            break
        if token.kind == "SYMBOL" and token.text == "}":
            if top_level:
                raise HclSyntaxError("unexpected '}'", _position(token, file))
            return items, index + 1
        if token.kind != "IDENT":
            raise HclSyntaxError(
                f"expected an attribute or block, found {token.text!r}", _position(token, file)
            )

        cursor = index
        header: list = []
        while True:
            current = tokens[cursor]
            if current.kind in ("NEWLINE", "EOF") or (
                current.kind == "SYMBOL" and current.text == "}"
            ):
                raise HclSyntaxError(
                    "expected '=' or '{' to start an attribute/block",
                    _position(current, file),
                )
            if current.kind == "SYMBOL" and current.text in ("=", "{"):
                break
            header.append(current)
            cursor += 1

        terminator = tokens[cursor]
        if terminator.text == "=":
            name = source[header[0].start : terminator.start].strip()
            value_start = terminator.end
            end_index, end_offset = _scan_value(tokens, cursor + 1, source, file)
            if end_index == cursor + 1:
                raise HclSyntaxError(
                    f"attribute {name!r} has no value", _position(terminator, file)
                )
            raw = source[value_start:end_offset]
            items.append(Attribute(name=name, raw=raw, position=_position(header[0], file)))
            index = end_index
            if index < len(tokens) and tokens[index].kind == "NEWLINE":
                index += 1
            continue

        block_type = header[0]
        if block_type.kind != "IDENT":
            raise HclSyntaxError("block type must be an identifier", _position(block_type, file))
        labels: list = []
        for label_token in header[1:]:
            if label_token.kind == "STRING":
                labels.append(label_token.value)
            elif label_token.kind == "IDENT":
                labels.append(label_token.text)
            else:
                raise HclSyntaxError(
                    f"invalid block label {label_token.text!r}", _position(label_token, file)
                )
        body, index = _parse_body(
            tokens, cursor + 1, source, file, top_level=False, open_token=terminator
        )
        items.append(
            Block(
                type=block_type.text,
                labels=tuple(labels),
                body=tuple(body),
                position=_position(block_type, file),
            )
        )
        if index < len(tokens) and tokens[index].kind == "NEWLINE":
            index += 1
    if not top_level:
        where = _position(open_token, file) if open_token is not None else None
        raise HclSyntaxError("missing closing '}'", where)
    return items, index


def _scan_value(tokens: list, index: int, source: str, file: str) -> tuple:
    """Return ``(next_index, end_offset)`` for an attribute value expression."""
    depth = 0
    start_index = index
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "EOF":
            break
        if token.kind == "NEWLINE" and depth == 0:
            break
        if token.kind == "SYMBOL":
            if token.text in "([{":
                depth += 1
            elif token.text in ")]}":
                if depth == 0:
                    break
                depth -= 1
        index += 1
    if index == start_index:
        return index, tokens[index].start if index < len(tokens) else len(source)
    return index, tokens[index - 1].end
