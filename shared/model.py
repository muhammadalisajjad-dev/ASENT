"""Terraform project model: nodes, module paths, references, moved edges.

The model is intentionally limited to the structure SABLE needs for the
bounded S3/IAM obligation problem: resource/data addresses, attributes,
nested blocks, local module expansion, reference edges and ``moved`` blocks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .errors import InputError, UnsupportedTerraformError
from .hcl import Attribute, Block, Position, parse_string
from .values import Value, flatten, iter_refs, parse_value, ref_address, ref_kind


@dataclass
class BodyModel:
    """Parsed body of a block: attributes plus nested blocks (ordered)."""

    attrs: dict
    blocks: list
    positions: dict = field(default_factory=dict)

    def attr(self, name: str):
        return self.attrs.get(name)

    def raw(self, name: str):
        value = self.attrs.get(name)
        return value

    def blocks_of(self, block_type: str) -> list:
        return [body for kind, _labels, body in self.blocks if kind == block_type]

    def walk(self, prefix: str = "") -> Iterator:
        """Yield ``(path, value)`` for every attribute in this body tree."""
        for name, value in self.attrs.items():
            path = f"{prefix}.{name}" if prefix else name
            yield path, value
        for index, (kind, labels, body) in enumerate(self.blocks):
            label = "/".join(labels)
            base = f"{kind}[{label}]" if label else f"{kind}"
            path = f"{prefix}.{base}" if prefix else base
            yield from body.walk(path)


@dataclass
class Node:
    """A single Terraform node (resource, data source, module, ...)."""

    address: str
    kind: str
    type: str | None
    name: str | None
    module_path: tuple
    file: str
    line: int
    ordinal: int
    body: BodyModel
    refs: tuple = ()
    ref_kinds: tuple = ()

    @property
    def path(self) -> str:
        return self.address

    def signature(self) -> dict:
        """Normalized ``{path: leaf}`` attribute signature for evidence."""
        out: dict = {}
        for path, value in self.body.walk():
            flatten(value, path, out)
        if not out:
            out["<empty>"] = "<empty>"
        return out


@dataclass
class MoveEdge:
    """Explicit ``moved`` information (from Terraform or change-info file)."""

    from_address: str
    to_address: str
    position: Position | None
    source: str  # "moved_block" | "change_info"

    def as_dict(self) -> dict:
        return {
            "from": self.from_address,
            "to": self.to_address,
            "source": self.source,
            "position": str(self.position) if self.position else None,
        }


@dataclass
class Project:
    """A parsed Terraform configuration directory."""

    root: str
    nodes: dict
    moved: list
    module_inputs: dict
    warnings: list
    unresolved_modules: list
    files: dict
    content_hash: str

    def get(self, address: str):
        return self.nodes.get(address)

    def of_type(self, resource_type: str) -> list:
        return [
            node
            for node in self.nodes.values()
            if node.kind == "resource" and node.type == resource_type
        ]

    def data_of_type(self, resource_type: str) -> list:
        return [
            node
            for node in self.nodes.values()
            if node.kind == "data" and node.type == resource_type
        ]

    def resources(self) -> list:
        return [node for node in self.nodes.values() if node.kind == "resource"]

    def incoming(self, address: str) -> list:
        return [node for node in self.nodes.values() if address in node.refs]

    def outgoing(self, node: Node) -> list:
        return [self.nodes[ref] for ref in node.refs if ref in self.nodes]


def _model_body(items: list) -> BodyModel:
    attrs: dict = {}
    blocks: list = []
    positions: dict = {}
    for item in items:
        if isinstance(item, Attribute):
            attrs[item.name] = parse_value(item.raw, item.position.file)
            positions[item.name] = item.position
        elif isinstance(item, Block):
            blocks.append((item.type, item.labels, _model_body(list(item.body))))
            positions.setdefault(item.type, item.position)
    return BodyModel(attrs=attrs, blocks=blocks, positions=positions)


def _qualify(module_path: tuple) -> str:
    return "".join(f"module.{name}." for name in module_path)


def _block_address(block: Block, module_path: tuple) -> tuple:
    """Return ``(kind, type, name, address)`` for a top-level block."""
    prefix = _qualify(module_path)
    if block.type in ("resource", "data"):
        if len(block.labels) != 2:
            raise UnsupportedTerraformError(
                f"{block.position}: '{block.type}' block requires exactly 2 labels, "
                f"found {len(block.labels)}"
            )
        kind = block.type
        type_name, name = block.labels[0], block.labels[1]
        if kind == "data":
            address = f"{prefix}data.{type_name}.{name}"
        else:
            address = f"{prefix}{type_name}.{name}"
        return kind, type_name, name, address
    if block.type == "module":
        if len(block.labels) != 1:
            raise UnsupportedTerraformError(
                f"{block.position}: 'module' block requires exactly 1 label"
            )
        return "module", None, block.labels[0], f"{prefix}module.{block.labels[0]}"
    if block.type == "variable":
        return "variable", None, block.labels[0], f"{prefix}var.{block.labels[0]}"
    if block.type == "output":
        return "output", None, block.labels[0], f"{prefix}output.{block.labels[0]}"
    return block.type, None, (block.labels[0] if block.labels else None), None


def build_project(directory: str | Path, max_module_depth: int = 8) -> Project:
    """Parse a Terraform directory (with local modules) into a :class:`Project`."""
    root = Path(directory)
    if not root.is_dir():
        raise InputError(f"not a directory: {root}")
    nodes: dict = {}
    moved: list = []
    module_inputs: dict = {}
    warnings: list = []
    unresolved: list = []
    files: dict = {}
    seen_paths: set = set()

    def ingest(scope_dir: Path, module_path: tuple, depth: int) -> None:
        if depth > max_module_depth:
            raise UnsupportedTerraformError(
                f"module nesting deeper than {max_module_depth} levels at {scope_dir}"
            )
        key = (str(scope_dir.resolve()), module_path)
        if key in seen_paths:
            return
        seen_paths.add(key)

        parsed_files: dict = {}
        for tf_file in sorted(scope_dir.glob("*.tf")):
            text = tf_file.read_text(encoding="utf-8")
            try:
                rel = str(tf_file.relative_to(root))
            except ValueError:
                rel = tf_file.name
            files[rel] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            parsed_files[tf_file.name] = parse_string(text, file=str(tf_file))

        for file_name in sorted(parsed_files):
            for item in parsed_files[file_name]:
                if not isinstance(item, Block):
                    continue
                if item.type == "moved":
                    edge = _moved_edge(item, module_path)
                    if edge is not None:
                        moved.append(edge)
                    continue
                if item.type in ("locals", "provider", "terraform", "removed", "import"):
                    continue
                kind, type_name, name, address = _block_address(item, module_path)
                if address is None:
                    continue
                if address in nodes:
                    raise UnsupportedTerraformError(
                        f"{item.position}: duplicate block address {address}"
                    )
                body = _model_body(list(item.body))
                node = Node(
                    address=address,
                    kind=kind,
                    type=type_name,
                    name=name,
                    module_path=module_path,
                    file=Path(item.position.file).name,
                    line=item.position.line,
                    ordinal=0,
                    body=body,
                )
                nodes[address] = node

                if kind == "module":
                    _register_module(
                        item,
                        node,
                        scope_dir,
                        module_path,
                        depth,
                        ingest,
                        module_inputs,
                        warnings,
                        unresolved,
                    )

    ingest(root, (), 0)
    _finalize(nodes, moved, module_inputs, warnings, unresolved, root, files)
    return Project(
        root=str(root),
        nodes=nodes,
        moved=moved,
        module_inputs=module_inputs,
        warnings=warnings,
        unresolved_modules=unresolved,
        files=files,
        content_hash=_content_hash(files),
    )


def _register_module(
    item: Block,
    node: Node,
    scope_dir: Path,
    module_path: tuple,
    depth: int,
    ingest,
    module_inputs: dict,
    warnings: list,
    unresolved: list,
) -> None:
    source_attr = node.body.attr("source")
    source = None
    if source_attr is not None:
        from .values import literal_string

        source = literal_string(source_attr)
    if source is None:
        warnings.append(f"{node.address}: module source is not a literal; module not expanded")
        unresolved.append(node.address)
        return
    child_path = module_path + (node.name,)
    module_inputs[child_path] = {
        name: value for name, value in node.body.attrs.items() if name != "source"
    }
    if source.startswith("./") or source.startswith("../") or source.startswith(".\\"):
        target = (scope_dir / source).resolve()
        if not target.is_dir():
            warnings.append(f"{node.address}: local module source not found: {source}")
            unresolved.append(node.address)
            return
        ingest(target, child_path, depth + 1)
        return
    warnings.append(f"{node.address}: non-local module source '{source}' not expanded")
    unresolved.append(node.address)


def _moved_edge(item: Block, module_path: tuple) -> MoveEdge | None:
    body = _model_body(list(item.body))
    from_value = body.attr("from")
    to_value = body.attr("to")
    if from_value is None or to_value is None:
        return None
    from_address = _address_from_value(from_value, module_path)
    to_address = _address_from_value(to_value, module_path)
    if from_address is None or to_address is None:
        return None
    return MoveEdge(
        from_address=from_address,
        to_address=to_address,
        position=item.position,
        source="moved_block",
    )


def _address_from_value(value, module_path: tuple) -> str | None:
    from .values import Ref, literal_string, ref_address

    if isinstance(value, Ref):
        return ref_address(value.path, module_path)
    text = literal_string(value)
    if text is None:
        return None
    path = tuple(segment for segment in text.split(".") if segment)
    return ref_address(path, module_path)


def move_edges_from_change_info(data: dict) -> list:
    """Build move edges from an explicit change-information JSON document."""
    edges: list = []
    entries = data.get("moved") if isinstance(data, dict) else None
    if entries is None:
        raise InputError("change-info file must contain a 'moved' list")
    if not isinstance(entries, list):
        raise InputError("change-info 'moved' must be a list")
    for entry in entries:
        if not isinstance(entry, dict) or "from" not in entry or "to" not in entry:
            raise InputError("each change-info moved entry needs 'from' and 'to'")
        edges.append(
            MoveEdge(
                from_address=str(entry["from"]),
                to_address=str(entry["to"]),
                position=None,
                source="change_info",
            )
        )
    return edges


def _finalize(nodes: dict, moved: list, module_inputs: dict, warnings: list, unresolved: list, root: Path, files: dict) -> None:
    # Reference extraction with scope qualification.  References through a
    # local module output are resolved to the referenced internal node so the
    # reference graph reflects real structural relationships.
    for node in nodes.values():
        refs: list = []
        kinds: list = []
        for _path, value in node.body.walk():
            for ref in iter_refs(value):
                address = ref_address(ref.path, node.module_path)
                kind = ref_kind(ref.path)
                if address is not None and address != node.address:
                    resolved, resolved_kind = _resolve_module_output(
                        ref.path, address, node.module_path, nodes
                    )
                    if resolved is not None:
                        address = resolved
                        if resolved_kind is not None:
                            kind = resolved_kind
                if kind is not None:
                    kinds.append(kind)
                if address is not None and address != node.address:
                    refs.append(address)
        node.refs = tuple(dict.fromkeys(refs))
        node.ref_kinds = tuple(sorted(dict.fromkeys(kinds)))

    # Ordinals among nodes of the same (kind, type) family.
    groups: dict = {}
    for node in nodes.values():
        key = (node.kind, node.type)
        groups.setdefault(key, []).append(node)
    for group in groups.values():
        group.sort(key=lambda n: (n.file, n.line, n.address))
        for index, node in enumerate(group):
            node.ordinal = index


def _resolve_module_output(path: tuple, address: str, module_path: tuple, nodes: dict):
    """Resolve ``module.<name>.<output>`` references to their target node."""
    from .values import Ref, Template, ref_address as _ref_address, ref_kind as _ref_kind

    if not path or path[0] != "module" or len(path) < 3:
        return address, None
    output_address = f"{address}.output.{path[2]}"
    node = nodes.get(output_address)
    if node is None:
        return address, None
    value = node.body.attr("value")
    target_path = None
    if isinstance(value, Ref):
        target_path = value.path
    elif isinstance(value, Template):
        refs = [part for part in value.parts if not isinstance(part, str)]
        if len(refs) == 1 and len(value.parts) == 2:
            only = refs[0]
            if isinstance(only, Ref):
                target_path = only.path
    if target_path is None:
        return address, None
    child_scope = node.module_path
    target = _ref_address(target_path, child_scope)
    if target is None:
        return address, None
    return target, _ref_kind(target_path)


def _content_hash(files: dict) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode("utf-8"))
        digest.update(files[name].encode("utf-8"))
    return digest.hexdigest()


def load_json(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise InputError(f"file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"{path}: expected a JSON object")
    return data
