# Tool side effects contract (autonomy plan a3)

Every tool node in a DAG must **declare side effects** and **rollback possibility**. If a tool is not rollbackable, it must be the **last** node in its path or guarded by an **approval gate** (e.g. HITL checkpoint).

## Declaration

- **Side effects:** One of `none` (pure/read-only), `read` (external reads only), `write` (external writes: filesystem, network, API).
- **Rollback:** Either `rollbackable` (effects can be undone or compensated) or `not_rollbackable`. When `not_rollbackable`, the node must not be followed by other side-effect nodes without an approval gate, or it must be the terminal node.

## Enforcement

- DAG validation (or review) should reject graphs where a non-rollbackable write node is followed by another write node without an intervening gate or terminal.
- Document in node config or graph-level policy; enforce in validator when schema supports it.

## Examples

- **memory_summary:** side_effects: none, rollback: N/A.
- **run_script** (post): side_effects: write (network), rollback: not_rollbackable → must be last or after checkpoint.
- **read_feedback:** side_effects: none, rollback: N/A.
