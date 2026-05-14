#!/usr/bin/env python3
"""
Obsidian Canvas Layout — graph-based auto-layout using topological layering.
Assigns rows based on edge flow (DAG layers), not y-position clustering.

Usage:
  python3 canvas-layout.py <canvas_file>
  python3 canvas-layout.py <canvas_file> --row-gap 220 --col-gap 180 --center-x 0 --dry-run
"""

import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict, deque


# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_ROW_GAP  = 220   # vertical gap between bottom of row N and top of row N+1
DEFAULT_COL_GAP  = 180   # horizontal gap between nodes in the same row
DEFAULT_CENTER_X = 0     # x origin rows are centered around
START_Y          = -800  # y coordinate of the first (topmost) row


# ── Graph helpers ─────────────────────────────────────────────────────────────

def build_graph(nodes: list, edges: list) -> tuple[dict, dict, set]:
    """
    Returns:
        children  : {node_id: [child_id, ...]}
        in_degree : {node_id: int}
        all_ids   : set of all node ids
    """
    all_ids   = {n["id"] for n in nodes}
    children  = defaultdict(list)
    in_degree = {n["id"]: 0 for n in nodes}

    for edge in edges:
        src = edge.get("fromNode")
        dst = edge.get("toNode")
        if src in all_ids and dst in all_ids:
            children[src].append(dst)
            in_degree[dst] += 1

    return dict(children), in_degree, all_ids


def assign_layers(nodes: list, edges: list) -> dict[str, int]:
    """
    Assign a layer index to each node using iterative longest-path.
    Handles cycles by only considering already-assigned predecessors.
    Layer 0 = root nodes (no incoming edges).
    """
    all_ids = {n["id"] for n in nodes}

    # Build predecessor map: node_id → set of nodes that point TO it
    predecessors: dict[str, set] = defaultdict(set)
    for edge in edges:
        src = edge.get("fromNode")
        dst = edge.get("toNode")
        if src in all_ids and dst in all_ids and src != dst:
            predecessors[dst].add(src)

    layer: dict[str, int] = {}

    # Seed: nodes with no predecessors → layer 0
    for node_id in all_ids:
        if not predecessors[node_id]:
            layer[node_id] = 0

    # Iteratively propagate layers until stable (handles cycles)
    for _ in range(len(all_ids) + 1):
        changed = False
        for node_id in all_ids:
            if node_id in layer:
                continue
            assigned_preds = [p for p in predecessors[node_id] if p in layer]
            if assigned_preds:
                new_layer = max(layer[p] for p in assigned_preds) + 1
                layer[node_id] = new_layer
                changed = True
        if not changed:
            break

    # Fallback: pure isolated cycles with no external entry → layer 0
    for node_id in all_ids:
        if node_id not in layer:
            layer[node_id] = 0

    return layer


# ── Layout ────────────────────────────────────────────────────────────────────

def compute_positions(
    nodes: list,
    layer_map: dict[str, int],
    row_gap: int,
    col_gap: int,
    center_x: int,
) -> dict[str, tuple[int, int]]:
    """
    Compute new (x, y) for every node.
    Returns {node_id: (x, y)}.
    """
    # Group nodes by layer, sorted by original x (preserve left-right order)
    layers: dict[int, list] = defaultdict(list)
    for node in nodes:
        layer_idx = layer_map.get(node["id"], 0)
        layers[layer_idx].append(node)

    for layer_nodes in layers.values():
        layer_nodes.sort(key=lambda n: n.get("x", 0))

    # Assign y positions top-to-bottom
    y_cursor = START_Y
    layer_y: dict[int, int] = {}

    for layer_idx in sorted(layers.keys()):
        layer_y[layer_idx] = y_cursor
        max_height = max(n.get("height", 100) for n in layers[layer_idx])
        y_cursor += max_height + row_gap

    # Assign x positions (center each row)
    positions: dict[str, tuple[int, int]] = {}

    for layer_idx, layer_nodes in layers.items():
        row_y = layer_y[layer_idx]
        total_width = (
            sum(n.get("width", 280) for n in layer_nodes)
            + col_gap * (len(layer_nodes) - 1)
        )
        x_cursor = center_x - total_width // 2

        for node in layer_nodes:
            positions[node["id"]] = (x_cursor, row_y)
            x_cursor += node.get("width", 280) + col_gap

    return positions


# ── Main ──────────────────────────────────────────────────────────────────────

def layout_canvas(
    canvas_path: str,
    row_gap: int,
    col_gap: int,
    center_x: int,
    dry_run: bool,
):
    path = Path(canvas_path)
    with open(path) as f:
        data = json.load(f)

    all_nodes = data.get("nodes", [])
    edges     = data.get("edges", [])

    # Skip group nodes — they are containers, not flow nodes
    flow_nodes  = [n for n in all_nodes if n.get("type") != "group"]
    group_nodes = [n for n in all_nodes if n.get("type") == "group"]

    # Assign layers via graph traversal
    layer_map = assign_layers(flow_nodes, edges)

    # Build layer summary for display
    layers_summary: dict[int, list[str]] = defaultdict(list)
    for node_id, layer_idx in layer_map.items():
        layers_summary[layer_idx].append(node_id)

    print(f"\nCanvas layout: {path}")
    print(f"Detected {len(layers_summary)} layers (graph-based):")
    for layer_idx in sorted(layers_summary.keys()):
        names = ", ".join(layers_summary[layer_idx])
        print(f"  Layer {layer_idx}: {names}")

    # Compute new positions
    positions = compute_positions(flow_nodes, layer_map, row_gap, col_gap, center_x)

    if dry_run:
        print("\n[DRY RUN] New positions:")
        for node_id, (x, y) in sorted(positions.items(), key=lambda kv: layer_map[kv[0]]):
            layer_idx = layer_map[node_id]
            print(f"  Layer {layer_idx}  {node_id:<35} x={x:>6}, y={y:>6}")
        print("\nNo changes written.")
        return

    # Apply positions to nodes
    changed = 0
    for node in all_nodes:
        if node["id"] in positions:
            new_x, new_y = positions[node["id"]]
            if node["x"] != new_x or node["y"] != new_y:
                changed += 1
            node["x"] = new_x
            node["y"] = new_y

    # Write back
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nRepositioned {changed} nodes. Edges unchanged.")
    print(f"✅ Written to: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-layout Obsidian Canvas using graph-based layer assignment"
    )
    parser.add_argument("canvas", help="Path to .canvas file")
    parser.add_argument("--row-gap",   type=int, default=DEFAULT_ROW_GAP,  help=f"Vertical gap between rows (default: {DEFAULT_ROW_GAP})")
    parser.add_argument("--col-gap",   type=int, default=DEFAULT_COL_GAP,  help=f"Horizontal gap between nodes (default: {DEFAULT_COL_GAP})")
    parser.add_argument("--center-x",  type=int, default=DEFAULT_CENTER_X, help=f"X origin to center rows around (default: {DEFAULT_CENTER_X})")
    parser.add_argument("--dry-run",   action="store_true",                help="Print new positions without writing")
    args = parser.parse_args()

    layout_canvas(
        canvas_path=args.canvas,
        row_gap=args.row_gap,
        col_gap=args.col_gap,
        center_x=args.center_x,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
