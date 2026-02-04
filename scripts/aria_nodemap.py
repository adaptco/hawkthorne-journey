#!/usr/bin/env python3
"""Resolve key ARIA nodes from a workflow export and emit NodeMap/override JSON."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


JsonDict = Dict[str, Any]


@dataclasses.dataclass(frozen=True)
class NodeSignature:
    name: str
    class_type_predicate: Callable[[str], bool]
    required_inputs: Tuple[str, ...]
    widgets_predicate: Callable[[List[Any]], bool]


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float))


def _load_workflow(path: Path) -> JsonDict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_nodes(workflow: JsonDict) -> Dict[str, JsonDict]:
    if "nodes" in workflow and isinstance(workflow["nodes"], list):
        nodes: Dict[str, JsonDict] = {}
        for node in workflow["nodes"]:
            node_id = node.get("id")
            if node_id is None:
                continue
            nodes[str(node_id)] = node
        return nodes
    return {str(key): value for key, value in workflow.items() if isinstance(value, dict)}


def _workflow_fingerprint(workflow: JsonDict) -> str:
    canonical = json.dumps(workflow, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _matches_signature(node: JsonDict, signature: NodeSignature) -> bool:
    class_type = node.get("class_type", "")
    if not isinstance(class_type, str) or not signature.class_type_predicate(class_type):
        return False

    inputs = node.get("inputs", {})
    if not isinstance(inputs, dict):
        return False

    for required in signature.required_inputs:
        if required not in inputs:
            return False

    widgets = _ensure_list(node.get("widgets_values"))
    return signature.widgets_predicate(widgets)


def _first_widget_string(widgets: List[Any]) -> bool:
    return bool(widgets) and isinstance(widgets[0], str)


def _sampler_widgets(widgets: List[Any]) -> bool:
    return bool(widgets) and _is_numeric(widgets[0])


def _camera_widgets(widgets: List[Any]) -> bool:
    if len(widgets) < 4:
        return False
    return all(_is_numeric(value) for value in widgets[:4])


def _default_signatures() -> Tuple[NodeSignature, NodeSignature, NodeSignature]:
    sampler_signature = NodeSignature(
        name="seed_node",
        class_type_predicate=lambda class_type: "sampler" in class_type.lower(),
        required_inputs=("model", "positive", "negative"),
        widgets_predicate=_sampler_widgets,
    )
    positive_prompt_signature = NodeSignature(
        name="positive_prompt_node",
        class_type_predicate=lambda class_type: class_type == "CLIPTextEncode",
        required_inputs=("clip",),
        widgets_predicate=_first_widget_string,
    )
    camera_signature = NodeSignature(
        name="camera_node",
        class_type_predicate=lambda class_type: any(
            token in class_type.lower() for token in ("camera", "transform", "pose")
        ),
        required_inputs=(),
        widgets_predicate=_camera_widgets,
    )
    return sampler_signature, positive_prompt_signature, camera_signature


def _find_candidates(nodes: Dict[str, JsonDict], signature: NodeSignature) -> List[str]:
    return [node_id for node_id, node in nodes.items() if _matches_signature(node, signature)]


def _resolve_node(
    nodes: Dict[str, JsonDict],
    signature: NodeSignature,
    explicit_id: Optional[str],
) -> Tuple[str, JsonDict]:
    if explicit_id:
        node = nodes.get(explicit_id)
        if not node:
            raise ValueError(f"Explicit {signature.name} id {explicit_id} not found.")
        if not _matches_signature(node, signature):
            raise ValueError(f"Explicit {signature.name} id {explicit_id} does not match signature.")
        return explicit_id, node

    candidates = _find_candidates(nodes, signature)
    if not candidates:
        raise ValueError(f"No nodes matched signature for {signature.name}.")
    if len(candidates) > 1:
        raise ValueError(
            f"Multiple nodes matched signature for {signature.name}: {candidates}. "
            "Provide --seed-node-id/--positive-node-id/--camera-node-id to disambiguate."
        )
    node_id = candidates[0]
    return node_id, nodes[node_id]


def _assert_widget_order(node: JsonDict, signature: NodeSignature) -> Optional[str]:
    widgets = _ensure_list(node.get("widgets_values"))
    if not signature.widgets_predicate(widgets):
        return f"{signature.name} widgets_values do not satisfy expected ordering."
    return None


def _build_node_entry(node_id: str, node: JsonDict, signature: NodeSignature) -> JsonDict:
    return {
        "id": int(node_id) if node_id.isdigit() else node_id,
        "class_type": node.get("class_type"),
        "inputs": sorted(node.get("inputs", {}).keys()) if isinstance(node.get("inputs"), dict) else [],
        "widgets_values": node.get("widgets_values", []),
        "signature": {
            "name": signature.name,
            "required_inputs": list(signature.required_inputs),
        },
    }


def _write_json(path: Path, payload: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate ARIA NodeMap/override artifacts from a workflow export.",
    )
    parser.add_argument("workflow", type=Path, help="Path to aria_workflow.json")
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--seed-node-id", help="Explicit node id for the sampler/seed node")
    parser.add_argument("--positive-node-id", help="Explicit node id for CLIPTextEncode")
    parser.add_argument("--camera-node-id", help="Explicit node id for camera/transform node")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = _parse_args(argv)
    workflow = _load_workflow(args.workflow)
    nodes = _normalize_nodes(workflow)
    fingerprint = _workflow_fingerprint(workflow)

    sampler_sig, clip_sig, camera_sig = _default_signatures()

    seed_id, seed_node = _resolve_node(nodes, sampler_sig, args.seed_node_id)
    positive_id, positive_node = _resolve_node(nodes, clip_sig, args.positive_node_id)
    camera_id, camera_node = _resolve_node(nodes, camera_sig, args.camera_node_id)

    errors: List[str] = []
    for node, signature in (
        (seed_node, sampler_sig),
        (positive_node, clip_sig),
        (camera_node, camera_sig),
    ):
        message = _assert_widget_order(node, signature)
        if message:
            errors.append(message)

    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1

    node_map = {
        "type": "ARIA_NodeMap.v1",
        "workflow_fingerprint": fingerprint,
        "nodes": {
            "seed_node": _build_node_entry(seed_id, seed_node, sampler_sig),
            "positive_prompt_node": _build_node_entry(positive_id, positive_node, clip_sig),
            "camera_node": _build_node_entry(camera_id, camera_node, camera_sig),
        },
    }

    override = {
        "type": "ARIA_NodeMapOverride.v1",
        "workflow_fingerprint": fingerprint,
        "pins": {
            "positive_prompt_node": int(positive_id)
            if str(positive_id).isdigit()
            else positive_id,
            "seed_node": int(seed_id) if str(seed_id).isdigit() else seed_id,
            "camera_node": int(camera_id) if str(camera_id).isdigit() else camera_id,
        },
    }

    _write_json(args.out_dir / "ARIA_NodeMap.v1.json", node_map)
    _write_json(args.out_dir / "ARIA_NodeMapOverride.v1.json", override)

    print(
        "Resolved nodes: "
        f"seed={seed_id}, positive={positive_id}, camera={camera_id}. "
        f"Fingerprint={fingerprint}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
