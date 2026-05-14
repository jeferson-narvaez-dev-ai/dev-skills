# obsidian-canvas

## Purpose

Create, edit, and manage Obsidian Canvas (.canvas) files in the vault.
Supports creating new canvases, adding nodes (text, file, link, group),
connecting nodes with edges, and editing existing canvases.

---

## Vault Resolution

Load `obsidian-file-system` skill first — it is the single source of truth for all paths and defines `$VAULT` and `$PROJECTS`.

- `$VAULT` — absolute path to the Obsidian vault (documentation only)
- `$PROJECTS` — absolute path to source code repositories

All note paths follow: `$VAULT/{project}/{branch-folder}/{type}/{name}-{date}.md`

---

## Note Type Taxonomy

Always ask the user which type applies if `note_type` is not provided:

| Type | When to use | Path pattern |
|------|------------|--------------|
| `exploration` | Initial research, code analysis, understanding how something works | `{project}/{branch}/exploration/{name}-{date}.canvas` |
| `plan` | Implementation plan based on prior exploration | `{project}/{branch}/plan/{name}-{date}.canvas` |
| `issue` | Bug analysis, incidents, production problems | `{project}/{branch}/issue/{name}-{date}.canvas` |
| `implementation` | Progress notes while implementing, decisions made during development | `{project}/{branch}/implementation/{name}-{date}.canvas` |
| `review` | PR reviews, post-mortems, retrospectives | `{project}/{branch}/review/{name}-{date}.canvas` |

**Natural flow:** `exploration` → `plan` → `implementation` (with `issue` for bugs, `review` for PR/retrospectives)

---

## Path Resolution

```bash
PROJECT=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "general")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
DATE=$(date +%Y-%m-%d)
```

Canvas files are always saved with `.canvas` extension instead of `.md`.

```bash
CANVAS_NAME="{canvas_name}"

case "{note_type}" in
  exploration)    RELATIVE_PATH="${PROJECT}/${BRANCH}/exploration/${CANVAS_NAME}-${DATE}.canvas" ;;
  plan)           RELATIVE_PATH="${PROJECT}/${BRANCH}/plan/${CANVAS_NAME}-${DATE}.canvas" ;;
  issue)          RELATIVE_PATH="${PROJECT}/${BRANCH}/issue/${CANVAS_NAME}-${DATE}.canvas" ;;
  implementation) RELATIVE_PATH="${PROJECT}/${BRANCH}/implementation/${CANVAS_NAME}-${DATE}.canvas" ;;
  review)         RELATIVE_PATH="${PROJECT}/${BRANCH}/review/${CANVAS_NAME}-${DATE}.canvas" ;;
esac

CANVAS_FILE="$VAULT/$RELATIVE_PATH"
```

---

## Operations

### 1. Create a New Canvas

1. Create a `.canvas` file with the base structure `{"nodes": [], "edges": []}`
2. Generate unique 16-character hex IDs for each node (e.g., `"6f0ad84f44ce9c17"`)
3. Add nodes with required fields: `id`, `type`, `x`, `y`, `width`, `height`
4. Add edges referencing valid node IDs via `fromNode` and `toNode`
5. **Validate**: Check manually — verify all IDs are unique, all required fields are present, and all `fromNode`/`toNode` values exist in the nodes array

### 2. Add a Node to an Existing Canvas

1. Read and parse the existing `.canvas` file
2. Generate a unique ID that does not collide with existing node or edge IDs
3. Choose position (`x`, `y`) that avoids overlapping existing nodes (leave 50-100px spacing)
4. Append the new node object to the `nodes` array
5. Optionally add edges connecting the new node to existing nodes
6. **Validate**: Check manually — confirm all IDs are unique and all edge references resolve to existing nodes

### 3. Connect Two Nodes

1. Identify the source and target node IDs
2. Generate a unique edge ID
3. Set `fromNode` and `toNode` to the source and target IDs
4. Optionally set `fromSide`/`toSide` (top, right, bottom, left) for anchor points
5. Optionally set `label` for descriptive text on the edge
6. Append the edge to the `edges` array
7. **Validate**: Check manually — confirm both `fromNode` and `toNode` reference existing node IDs

### 4. Edit an Existing Canvas

1. Read and parse the `.canvas` file as JSON
2. Locate the target node or edge by `id`
3. Modify the desired attributes (text, position, color, etc.)
4. Write the updated JSON back to the file
5. **Validate**: Check manually — re-verify all ID uniqueness and edge reference integrity after editing

---

## Nodes

Nodes are objects placed on the canvas. Array order determines z-index: first node = bottom layer, last node = top layer.

### Generic Node Attributes

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `id` | Yes | string | Unique 16-char hex identifier |
| `type` | Yes | string | `text`, `file`, `link`, or `group` |
| `x` | Yes | integer | X position in pixels |
| `y` | Yes | integer | Y position in pixels |
| `width` | Yes | integer | Width in pixels |
| `height` | Yes | integer | Height in pixels |
| `color` | No | canvasColor | Preset `"1"`-`"6"` or hex (e.g., `"#FF0000"`) |

### Text Nodes

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `text` | Yes | string | Plain text with Markdown syntax |

```json
{
  "id": "6f0ad84f44ce9c17",
  "type": "text",
  "x": 0,
  "y": 0,
  "width": 400,
  "height": 200,
  "text": "# Hello World\n\nThis is **Markdown** content."
}
```

**Newline pitfall**: Use `\n` for line breaks in JSON strings. Do **not** use the literal `\\n` — Obsidian renders that as the characters `\` and `n`.

### File Nodes

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `file` | Yes | string | Path to file within the system |
| `subpath` | No | string | Link to heading or block (starts with `#`) |

```json
{
  "id": "a1b2c3d4e5f67890",
  "type": "file",
  "x": 500,
  "y": 0,
  "width": 400,
  "height": 300,
  "file": "Attachments/diagram.png"
}
```

### Link Nodes

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `url` | Yes | string | External URL |

```json
{
  "id": "c3d4e5f678901234",
  "type": "link",
  "x": 1000,
  "y": 0,
  "width": 400,
  "height": 200,
  "url": "https://obsidian.md"
}
```

### Group Nodes

Groups are visual containers for organizing other nodes. Position child nodes inside the group's bounds.

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `label` | No | string | Text label for the group |
| `background` | No | string | Path to background image |
| `backgroundStyle` | No | string | `cover`, `ratio`, or `repeat` |

```json
{
  "id": "d4e5f6789012345a",
  "type": "group",
  "x": -50,
  "y": -50,
  "width": 1000,
  "height": 600,
  "label": "Project Overview",
  "color": "4"
}
```

---

## Edges

Edges connect nodes via `fromNode` and `toNode` IDs.

| Attribute | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| `id` | Yes | string | - | Unique identifier |
| `fromNode` | Yes | string | - | Source node ID |
| `fromSide` | No | string | - | `top`, `right`, `bottom`, or `left` |
| `fromEnd` | No | string | `none` | `none` or `arrow` |
| `toNode` | Yes | string | - | Target node ID |
| `toSide` | No | string | - | `top`, `right`, `bottom`, or `left` |
| `toEnd` | No | string | `arrow` | `none` or `arrow` |
| `color` | No | canvasColor | - | Line color |
| `label` | No | string | - | Text label |

```json
{
  "id": "0123456789abcdef",
  "fromNode": "6f0ad84f44ce9c17",
  "fromSide": "right",
  "toNode": "a1b2c3d4e5f67890",
  "toSide": "left",
  "toEnd": "arrow",
  "label": "leads to"
}
```

---

## Colors

| Preset | Color |
|--------|-------|
| `"1"` | Red |
| `"2"` | Orange |
| `"3"` | Yellow |
| `"4"` | Green |
| `"5"` | Cyan |
| `"6"` | Purple |

---

## Service Color Nomenclature

Use consistent colors to identify node types at a glance.
Obsidian canvas only supports presets `"1"`–`"6"`, so map service categories to the closest color.

Conventions are derived from the drawio skill's AWS fill color system:
- Compute (`#ED7100`) → Orange
- Messaging (`#E7157B`) → Green (closest warm/active preset)
- Database (`#2E73B8`) → Yellow (closest neutral/data preset)
- Storage (`#3F8624`) → Yellow (data-at-rest, same tier as DB)
- Security/Errors (`#DD344C`) → Red
- Networking/Actors/Groups (`#8C4FFF`) → Purple
- API/Services → Cyan

| Service Category        | Color Preset | Color   | Examples |
|------------------------|-------------|---------|---------|
| API Gateway / HTTP     | `"5"`       | Cyan    | REST endpoints, API routes |
| Lambda / Compute       | `"2"`       | Orange  | Lambda handlers, functions |
| SQS / Messaging        | `"4"`       | Green   | SQS queues, event buses, SNS |
| DynamoDB / Database    | `"3"`       | Yellow  | DynamoDB tables, RDS, caches |
| S3 / Storage           | `"3"`       | Yellow  | S3 buckets, file storage |
| External API / Bank    | `"1"`       | Red     | Third-party APIs, bank APIs |
| Microservice / Service | `"5"`       | Cyan    | Internal microservices |
| Step Function / Batch  | `"2"`       | Orange  | Step Functions, cron jobs, schedulers |
| Merchant / Actor       | `"6"`       | Purple  | End users, merchants, external actors |
| Notification / Alerts  | `"4"`       | Green   | Notification services, email, webhooks |
| Error / DLQ            | `"1"`       | Red     | Dead-letter queues, error handlers |
| Group / Domain         | `"6"`       | Purple  | Logical groups, bounded contexts |

> These mappings are conventions — override per project if needed. The goal is visual consistency: compute = orange, messaging = green, storage = yellow, external/errors = red, actors/groups = purple, API/services = cyan.

---

## ID Generation

Generate 16-character lowercase hexadecimal strings (64-bit random value):

```python
import secrets
node_id = secrets.token_hex(8)  # e.g. "6f0ad84f44ce9c17"
```

Or in bash:
```bash
openssl rand -hex 8
```

---

## Layout Guidelines

- Coordinates can be negative (canvas extends infinitely)
- `x` increases right, `y` increases down; position is the top-left corner
- Space nodes **minimum 150px apart** horizontally and **minimum 200px apart** vertically
- Align to grid (multiples of 20) for cleaner layouts
- Column spacing: use **500px between column x-origins** (e.g. x=0, x=500, x=1000)
- Row spacing: use **350px between row y-origins** (e.g. y=0, y=350, y=700)

### Node Sizing by Text Content

Node dimensions must accommodate the full text. Use these formulas:

**Width** — based on the longest line in the text:

| Longest line (chars) | Recommended width |
|---------------------|-------------------|
| ≤ 20 chars | 240px |
| 21–35 chars | 320px |
| 36–50 chars | 420px |
| 51–65 chars | 520px |
| > 65 chars | 620px |

**Height** — based on number of lines rendered (count `\n` breaks + 1, plus heading padding):

| Rendered lines | Recommended height |
|---------------|-------------------|
| 1–2 lines | 80px |
| 3–4 lines | 130px |
| 5–6 lines | 180px |
| 7–8 lines | 230px |
| > 8 lines | 280px+ |

> **Heading rule**: Each `##` heading adds ~40px of visual height. Add 40px per heading found in the text.
>
> **Code block rule**: Inline code (backtick lines) wraps at ~60 chars. Account for wrapping when estimating line count.
>
> **Minimum padding**: Always add +40px to calculated height as bottom padding buffer.

### Sizing Examples

```
text: "## Merchant\nInitiates payout request"
→ longest line: "Initiates payout request" = 24 chars → width: 320px
→ lines: heading (40px) + 1 line (30px) + padding (40px) = 110px height
→ result: width=320, height=110
```

```
text: "## DynamoDB\n`usrv-payouts-transfer-transactions`\nStatus: PENDING → PROCESSING → SUCCESS/DECLINED"
→ longest line: "Status: PENDING → PROCESSING → SUCCESS/DECLINED" = 49 chars → width: 420px
→ lines: heading (40px) + code line (35px) + text line (30px) + padding (40px) = 145px height
→ result: width=420, height=150
```

```
text: "## Itau Bank API\nExternal REST API\nVPC-isolated\nInit / GetStatus / ProcessFailed"
→ longest line: "Init / GetStatus / ProcessFailed" = 32 chars → width: 320px
→ lines: heading (40px) + 3 lines (90px) + padding (40px) = 170px height
→ result: width=320, height=170
```

### File Node Sizing

File nodes render a preview of the linked note. Use these defaults:

| Content type | Width | Height |
|-------------|-------|--------|
| Short note preview | 320px | 100px |
| Standard note | 380px | 130px |
| Long/complex note | 450px | 160px |

### Quick Reference

| Node type | Width | Height |
|-----------|-------|--------|
| Actor / user (2 lines) | 280px | 110px |
| SQS / queue (3 lines) | 380px | 140px |
| Lambda handler (3 lines) | 380px | 140px |
| DynamoDB table (3 lines, long text) | 440px | 160px |
| External API (4 lines) | 340px | 170px |
| Step Function / batch (4 lines) | 340px | 170px |
| Microservice file node | 380px | 130px |

---

## Layout Styles

Choose a layout style based on the diagram type. Each style has specific spacing, direction, and grouping rules.

---

### Style 1: Vertical Flow (default)
**Direction:** Top → Bottom  
**Use when:** Sequential processes, pipelines, event-driven flows, CI/CD, payout flows  
**Avoid when:** More than 8 layers deep (canvas gets too tall to navigate)

| Parameter | Value |
|-----------|-------|
| Layer direction | Top → Bottom |
| Column x-spacing | 500px between column origins |
| Row y-spacing | 350px between row origins |
| Node alignment | Centered horizontally per row |
| Edge sides | `fromSide: bottom` → `toSide: top` |

```json
{ "x": 0, "y": 0 }       // Row 0
{ "x": 0, "y": 350 }     // Row 1
{ "x": 0, "y": 700 }     // Row 2
```

---

### Style 2: Horizontal Flow
**Direction:** Left → Right  
**Use when:** Request/response cycles, left-to-right user journeys, API chains, state machines  
**Avoid when:** More than 6 stages wide (nodes go off-screen)

| Parameter | Value |
|-----------|-------|
| Layer direction | Left → Right |
| Column x-spacing | node_width + 200px gap |
| Row y-spacing | node_height + 150px gap |
| Node alignment | Centered vertically per column |
| Edge sides | `fromSide: right` → `toSide: left` |

```json
{ "x": 0,    "y": 0 }   // Stage 0
{ "x": 500,  "y": 0 }   // Stage 1
{ "x": 1000, "y": 0 }   // Stage 2
```

---

### Style 3: Mermaid-style (compact grid)
**Direction:** Top → Bottom, tight spacing  
**Use when:** Documenting code logic, simple flowcharts, decision trees, quick exploration notes  
**Avoid when:** Nodes have long text (they'll feel cramped)

| Parameter | Value |
|-----------|-------|
| Layer direction | Top → Bottom |
| Column x-spacing | node_width + 80px gap |
| Row y-spacing | node_height + 60px gap |
| Node alignment | Left-aligned (no centering) |
| Edge sides | `fromSide: bottom` → `toSide: top` |
| Node size | Use minimum sizes (small text nodes: 200×80) |

```json
{ "x": 0,   "y": 0 }    // Row 0
{ "x": 0,   "y": 140 }  // Row 1  (80px node + 60px gap)
{ "x": 280, "y": 0 }    // Column 1, Row 0
```

---

### Style 4: C4 Diagram
**Direction:** Layered with group containers  
**Use when:** System context maps, software architecture at Person/System/Container/Component level  
**Avoid when:** You don't need explicit boundary containers

**Layers:**
- **Level 1 — Context**: People (color `"6"`) + External Systems (color `"1"`)
- **Level 2 — Containers**: Internal services inside a `group` node (color `"5"`)
- **Level 3 — Components**: Subcomponents inside containers

| Parameter | Value |
|-----------|-------|
| Group node padding | 60px around child nodes |
| Child spacing inside group | 150px col gap, 120px row gap |
| Between groups | 200px gap |
| Edge sides | `fromSide: right` → `toSide: left` (horizontal within level) |
| Group color | `"6"` (domain boundary), `"5"` (service boundary) |

**Node color mapping for C4:**
| C4 Element | Color |
|-----------|-------|
| Person / Actor | `"6"` Purple |
| External System | `"1"` Red |
| Internal System / Service | `"5"` Cyan |
| Container (API, DB, Queue) | `"2"` / `"3"` / `"4"` per type |
| Group boundary | `"6"` Purple |

---

### Style 5: Architecture Overview (Cloud zones)
**Direction:** Spatial zones, no strict flow direction  
**Use when:** Cloud infrastructure diagrams, multi-region setups, showing physical/logical boundaries  
**Avoid when:** You need to show a sequential process

**Zone layout:**
- Use `group` nodes as zone containers (VPC, region, account)
- Place services inside their zone group
- Connect cross-zone services with labeled edges
- Use large group nodes (1000×600 or more)

| Parameter | Value |
|-----------|-------|
| Zone group size | 800–1400px wide, 400–800px tall |
| Service inside zone | 200px from zone edge (padding) |
| Between zones | 150px gap |
| Zone color | `"6"` for network boundary, `"5"` for service cluster |

**Color mapping for cloud:**
| Resource | Color |
|----------|-------|
| VPC / Network zone | `"6"` Purple |
| Lambda / Compute | `"2"` Orange |
| SQS / EventBridge | `"4"` Green |
| DynamoDB / RDS | `"3"` Yellow |
| External / Internet | `"1"` Red |
| API Gateway / Load Balancer | `"5"` Cyan |

---

### Style 6: ER Diagram (Entity Relationship)
**Direction:** Spatial / grid  
**Use when:** Database schema, data models, domain object relationships  
**Avoid when:** You need to show process flow

**Entity node format:**
```
## TableName
---
PK  id: uuid
    name: string
    created_at: timestamp
FK  user_id → users.id
```

| Parameter | Value |
|-----------|-------|
| Node width | 300–400px (based on longest field line) |
| Node height | 40px per field + 80px header + 40px padding |
| Column spacing | 200px between entities |
| Row spacing | 150px between entities |
| Edge label | Relationship type: `1:N`, `N:M`, `1:1` |
| Entity color | `"3"` Yellow (table) / `"5"` Cyan (view) / `"1"` Red (external) |

---

### Choosing the Right Style

| Situation | Recommended Style |
|-----------|------------------|
| Microservice event flow | Vertical Flow |
| API request/response chain | Horizontal Flow |
| Code logic / decision tree | Mermaid-style |
| System architecture overview | C4 Diagram |
| Cloud infrastructure / AWS zones | Architecture Overview |
| Database schema | ER Diagram |
| CI/CD pipeline | Horizontal Flow |
| User journey | Horizontal Flow |
| Domain model | C4 Diagram (Component level) |
| Incident post-mortem timeline | Horizontal Flow |

> **Rule**: If the diagram has a clear start and end, use flow styles (1 or 2). If it shows structure/ownership boundaries, use C4 or Architecture. If it shows data relationships, use ER.

---

## Multi-Flow Canvas

A single canvas can contain **multiple independent flows** side by side. Each flow occupies its own spatial region, separated by a large horizontal or vertical gap (minimum 600px between flow regions).

### When to use

- Documenting several related use cases in one file (e.g., success flow + error flow + retry flow)
- Comparing before/after states of a system
- Showing multiple entry points to the same service
- Side-by-side variant flows of a feature

### Flow Regions

Each flow gets its own coordinate origin offset. By convention, flows are laid out **left to right** with a 800px gap between their rightmost and leftmost nodes.

| Flow | X Origin | Description |
|------|----------|-------------|
| Flow 1 | `x = 0` | Primary / happy path |
| Flow 2 | `x = flow1_width + 800` | Secondary flow |
| Flow 3 | `x = flow2_end + 800` | Tertiary flow |

> **flow1_width**: sum of column widths + gaps of flow 1. Estimate as `(num_columns × 500) + (num_columns - 1) × 200`.

### Flow Labels (required)

Each flow MUST have a **label group node** at the top of its region:

```json
{
  "id": "{generated-id}",
  "type": "group",
  "x": {flow_x_origin - 40},
  "y": -120,
  "width": {flow_estimated_width + 80},
  "height": 80,
  "label": "Flow 1: Happy Path",
  "color": "6"
}
```

Position the label group 120px above the first row of nodes (`y = -120`). This makes each flow identifiable at a glance.

### Node ID Uniqueness Across Flows

All node and edge IDs must be unique across the **entire file**, not just within a flow. When building flow 2+, generate fresh IDs — never copy-paste IDs from flow 1.

### Edges Between Flows

Do NOT connect nodes across flows with edges unless explicitly showing a cross-flow dependency. If a cross-flow edge is needed, use a dashed style (label it clearly, e.g., `"label": "→ see Flow 2"`).

### Multi-Flow Sizing Metrics

When calculating total canvas size for multi-flow layouts:

| Metric | Formula |
|--------|---------|
| Total canvas width | `Σ(flow_widths) + (num_flows - 1) × 800` |
| Flow width estimate | `num_columns × 500 + (num_columns - 1) × 200` |
| Flow height estimate | `num_rows × 350 + (num_rows - 1) × 100` |
| Label group width | `flow_width + 80` |
| Label group x offset | `flow_x_origin - 40` |

### Example: 3-Flow Layout

```
Flow 1: Happy Path         Flow 2: Error/Retry           Flow 3: Timeout
x=0 to x=1200             x=2000 to x=3200              x=4000 to x=5200
─────────────────         ─────────────────────         ──────────────────
[Actor] → [API] →         [Actor] → [API] →             [Actor] → [API] →
[Lambda] → [DB]           [Lambda] → [DLQ] →            [Lambda] → [Timeout
                          [Retry Lambda]                  Handler]
```

```json
// Flow 1 label group
{ "id": "flow1label", "type": "group", "x": -40, "y": -120, "width": 1280, "height": 80, "label": "Flow 1: Happy Path", "color": "6" }

// Flow 2 label group
{ "id": "flow2label", "type": "group", "x": 1960, "y": -120, "width": 1280, "height": 80, "label": "Flow 2: Error / Retry", "color": "1" }

// Flow 3 label group
{ "id": "flow3label", "type": "group", "x": 3960, "y": -120, "width": 1280, "height": 80, "label": "Flow 3: Timeout", "color": "3" }
```

### Color Conventions for Multi-Flow Labels

| Flow Type | Label Color |
|-----------|------------|
| Happy path / primary | `"6"` Purple |
| Error / failure | `"1"` Red |
| Retry / fallback | `"3"` Yellow |
| Async / background | `"4"` Green |
| Timeout / expiry | `"3"` Yellow |
| Alternative path | `"5"` Cyan |

---

## Markdown Linking

### When creating a new canvas

After resolving the canvas file path, check if a `.md` file with the same base name exists in the same folder:

```bash
MD_SIBLING="${CANVAS_FILE%.canvas}.md"
```

1. If it **exists** → add a `file` node to the canvas referencing that note:

   ```json
   {
     "id": "{generated-id}",
     "type": "file",
     "file": "{relative-path-from-vault-root}",
     "x": -200,
     "y": -200,
     "width": 380,
     "height": 130
   }
   ```

   Position it at the top-left corner of the canvas (x=-200, y=-200) as a "header" reference node.

2. Also update the sibling `.md` file: append `![[{canvas-base-name}.canvas]]` at the bottom if not already there.

### When a markdown note name is explicitly provided

Always add a `file` node for that note as described above.

---

## Validation Checklist

After creating or editing a canvas file, verify manually:

1. All `id` values are unique across **all** nodes and edges in the file (including across multiple flows)
2. Every `fromNode` and `toNode` references an existing node ID
3. Required fields are present for each node type (`text` for text nodes, `file` for file nodes, `url` for link nodes)
4. `type` is one of: `text`, `file`, `link`, `group`
5. `fromSide`/`toSide` values are one of: `top`, `right`, `bottom`, `left`
6. `fromEnd`/`toEnd` values are one of: `none`, `arrow`
7. Color presets are `"1"` through `"6"` or valid hex (e.g., `"#FF0000"`)
8. JSON is valid and well-formed (check brackets, commas, and quoted strings)
9. Node `width` accommodates the longest line of text (use the sizing table)
10. Node `height` accommodates all rendered lines including headings and padding
11. **Multi-flow**: Each flow has a label group node at `y = -120` above its nodes
12. **Multi-flow**: Flows are separated by at least 800px horizontal gap
13. **Multi-flow**: No edges connect across flows unless intentional cross-flow dependencies

If validation reveals issues, check for: duplicate IDs, dangling edge references, malformed JSON strings (especially unescaped newlines), or overlapping flow regions.

---

## References
- [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/)
- [JSON Canvas GitHub](https://github.com/obsidianmd/jsoncanvas)

---

## Rules

1. Always resolve vault path before any file operation (env var → config file → ask user).
2. Canvas files use `.canvas` extension, never `.md`.
3. Always validate JSON structure manually before writing — verify all IDs are unique and all edge references resolve.
4. Never reuse IDs — generate fresh 16-char hex for every new node and edge.
5. Always verify edge references point to existing node IDs before writing.
6. Use the same path taxonomy as `obsidian-save` — `$VAULT/$PROJECT/$BRANCH/{type}/` folder structure. Projects go directly under `$VAULT/` — no intermediate subfolder.
7. When creating a canvas from scratch, start with `{"nodes": [], "edges": []}` and build up.
8. When editing, always read → parse → modify → validate → write. Never patch the raw string.
9. Canvas and markdown notes with the same base name in the same folder are treated as a linked pair — always check for and maintain the sibling link.
10. When placing multiple flows in one canvas, assign each flow a unique X-origin offset (minimum 800px gap between flows) and label each flow with a group node at y=-120.
