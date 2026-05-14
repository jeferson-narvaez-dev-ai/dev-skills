#!/usr/bin/env python3
"""
Obsidian Canvas Node Sizer
Calculates optimal width and height for canvas text nodes based on content.
Usage: python3 node-sizer.py "## Node Title\nLine one\nLine two"
       python3 node-sizer.py  # interactive mode
"""

import sys
import math

# --- Constants ---
CHAR_WIDTH_PX = 8.5       # average px per character at default font size
LINE_HEIGHT_PX = 22       # px per rendered text line
HEADING_EXTRA_PX = 18     # extra px a ## heading adds over a normal line
CODE_CHAR_WIDTH_PX = 9.5  # monospace chars are slightly wider
PADDING_PX = 60           # total vertical padding (top + bottom)
H_PADDING_PX = 40         # total horizontal padding (left + right)
MAX_WRAP_WIDTH = 600       # px — lines wider than this wrap
MIN_WIDTH = 200
MIN_HEIGHT = 80


def is_heading(line: str) -> bool:
    return line.startswith("#")


def is_code(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("`") or stripped.startswith("```")


def rendered_line_width_px(line: str) -> float:
    """Estimate the rendered pixel width of a single line."""
    if is_code(line):
        return len(line) * CODE_CHAR_WIDTH_PX
    return len(line) * CHAR_WIDTH_PX


def line_height_px(line: str) -> float:
    """Estimate the rendered pixel height contribution of a single line."""
    base = LINE_HEIGHT_PX
    if is_heading(line):
        base += HEADING_EXTRA_PX
    return base


def calculate_node_size(text: str) -> dict:
    """
    Given the text content of a canvas node, return recommended width and height.
    Handles markdown headings, inline code, and line wrapping.
    """
    lines = text.split("\\n")  # JSON-escaped newlines
    if len(lines) == 1 and "\n" in text:
        lines = text.split("\n")

    total_height = PADDING_PX
    max_line_width_px = 0

    for line in lines:
        line_px_width = rendered_line_width_px(line)

        # Account for wrapping: if line is wider than MAX_WRAP_WIDTH, it wraps
        wrap_factor = math.ceil(line_px_width / MAX_WRAP_WIDTH) if line_px_width > 0 else 1
        wrapped_height = line_height_px(line) * wrap_factor
        total_height += wrapped_height

        max_line_width_px = max(max_line_width_px, min(line_px_width, MAX_WRAP_WIDTH))

    # Width: content width + horizontal padding, snapped to 20px grid
    raw_width = max_line_width_px + H_PADDING_PX
    width = max(MIN_WIDTH, snap_to_grid(raw_width, 20))

    # Height: total height, snapped to 10px grid
    height = max(MIN_HEIGHT, snap_to_grid(total_height, 10))

    return {
        "width": width,
        "height": height,
        "lines": len(lines),
        "longest_line": max(lines, key=len),
        "longest_line_chars": max(len(l) for l in lines),
        "longest_line_px": round(max_line_width_px),
    }


def snap_to_grid(value: float, grid: int) -> int:
    return int(math.ceil(value / grid) * grid)


def format_result(text: str, result: dict) -> str:
    lines_preview = text.replace("\\n", " | ").replace("\n", " | ")
    if len(lines_preview) > 60:
        lines_preview = lines_preview[:57] + "..."
    return (
        f"Input  : {lines_preview}\n"
        f"Lines  : {result['lines']}\n"
        f"Longest: \"{result['longest_line']}\" ({result['longest_line_chars']} chars, ~{result['longest_line_px']}px)\n"
        f"→ width : {result['width']}px\n"
        f"→ height: {result['height']}px\n"
    )


def batch_from_canvas(canvas_path: str):
    """Read a .canvas file and print recommended sizes for all text nodes."""
    import json
    with open(canvas_path) as f:
        data = json.load(f)

    print(f"{'ID':<30} {'W':>5} {'H':>5}   {'Rec W':>6} {'Rec H':>6}   {'Status'}")
    print("-" * 75)

    for node in data.get("nodes", []):
        if node.get("type") != "text":
            continue
        text = node.get("text", "")
        result = calculate_node_size(text)
        current_w = node.get("width", 0)
        current_h = node.get("height", 0)
        rec_w = result["width"]
        rec_h = result["height"]

        w_ok = "✅" if current_w >= rec_w else f"⚠️  (need +{rec_w - current_w})"
        h_ok = "✅" if current_h >= rec_h else f"⚠️  (need +{rec_h - current_h})"
        status = f"W:{w_ok}  H:{h_ok}"

        print(f"{node['id']:<30} {current_w:>5} {current_h:>5}   {rec_w:>6} {rec_h:>6}   {status}")


def canvas_gaps(canvas_path: str):
    """Analyze column gaps vs. edge label lengths and report which are too small."""
    import json
    import math

    LABEL_CHAR_PX = 8.5   # px per character for edge labels
    LABEL_PADDING = 80    # px padding around label
    MIN_GAP = 200         # minimum gap regardless of label length
    COL_TOLERANCE = 10    # px tolerance to group nodes into same column

    with open(canvas_path) as f:
        data = json.load(f)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if not nodes:
        print("No nodes found in canvas.")
        return

    # Group nodes into columns by x value (within tolerance)
    node_by_id = {n["id"]: n for n in nodes}

    # Collect unique x values, then cluster by tolerance
    all_x = sorted(set(n["x"] for n in nodes))
    clusters = []  # list of representative x values
    for x in all_x:
        if not clusters or x - clusters[-1] > COL_TOLERANCE:
            clusters.append(x)
    # Map each node's x to its cluster representative
    def cluster_for(x):
        for c in clusters:
            if abs(x - c) <= COL_TOLERANCE:
                return c
        return x

    node_col_x = {n["id"]: cluster_for(n["x"]) for n in nodes}
    sorted_col_x = sorted(clusters)
    col_index = {x: i for i, x in enumerate(sorted_col_x)}

    # Max width per column
    col_max_width = {}
    for n in nodes:
        cx = cluster_for(n["x"])
        col_max_width[cx] = max(col_max_width.get(cx, 0), n["width"])

    # For each edge, find the column pair and collect label
    pair_labels = {}  # (col_i, col_j) -> list of (label, chars)
    for edge in edges:
        fn = edge.get("fromNode")
        tn = edge.get("toNode")
        label = edge.get("label", "")
        if fn not in node_col_x or tn not in node_col_x:
            continue
        ci = col_index[node_col_x[fn]]
        cj = col_index[node_col_x[tn]]
        if ci == cj:
            continue
        pair = (min(ci, cj), max(ci, cj))
        pair_labels.setdefault(pair, []).append(label)

    print("Column Gap Analysis")
    print("===================")

    for i in range(len(sorted_col_x) - 1):
        x_left = sorted_col_x[i]
        x_right = sorted_col_x[i + 1]
        max_w_left = col_max_width[x_left]
        current_gap = x_right - (x_left + max_w_left)

        pair = (i, i + 1)
        labels = pair_labels.get(pair, [])
        if labels:
            longest_label = max(labels, key=len)
            longest_chars = len(longest_label)
        else:
            longest_label = "(no label)"
            longest_chars = 0

        min_needed = math.ceil(longest_chars * LABEL_CHAR_PX + LABEL_PADDING)
        required = max(MIN_GAP, min_needed)

        if current_gap >= required:
            status = "✅ OK"
        else:
            status = f"⚠️  TOO SMALL → need {required}px"

        label_display = f'"{longest_label}"' if longest_label != "(no label)" else longest_label
        print(
            f"Col {i}→{i+1}  (x={x_left}→{x_right})  gap={current_gap}px  "
            f"longest label: {label_display} ({longest_chars}c, {min_needed}px needed)  "
            f"{status}"
        )


# --- CLI ---
if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        # Interactive mode
        print("Obsidian Canvas Node Sizer — interactive mode")
        print("Enter node text (use \\n for newlines). Empty line to quit.\n")
        while True:
            try:
                text = input("Text: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                break
            result = calculate_node_size(text)
            print(format_result(text, result))

    elif args[0] == "--canvas" and len(args) == 2:
        # Audit mode: check an existing canvas file
        batch_from_canvas(args[1])

    elif args[0] == "--canvas-gaps" and len(args) == 2:
        # Gap analysis mode: check column gaps vs edge label lengths
        canvas_gaps(args[1])

    else:
        # Single text argument
        text = " ".join(args)
        result = calculate_node_size(text)
        print(format_result(text, result))
        print(f'JSON snippet:')
        print(f'  "width": {result["width"]},')
        print(f'  "height": {result["height"]}')
