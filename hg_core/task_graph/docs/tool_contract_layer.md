# Tool Contract Layer (MVP)

## Goal
Make tools safe and predictable in durable DAG runs by enforcing a contract at the adapter boundary.

Problems solved:
- inconsistent tool IO shapes
- retries causing duplicate side effects
- missing schemas leads to brittle planners and validators
- lack of rate limiting

## ToolDescriptor
A tool must declare:
- name: string
- description: string
- input_schema: JSON Schema (or pydantic model)
- output_schema: JSON Schema
- effect_class: none | read | write
- supports_idempotency_key: bool
- default_timeout_s: int (seconds)
- rate_limit: optional { requests_per_minute, burst }

## ToolRegistry
Registry of tool descriptors used by executor and planner.
- register(desc: ToolDescriptor) -> None — add tool by name (duplicate names are rejected)
- get(name: str) -> ToolDescriptor — return descriptor; raise KeyError if unknown
- list() -> list[ToolDescriptor] — return all registered tools
- describe_all() -> list[dict] — deterministic metadata snapshot for audits/UI

Validation on register:
- `name` must be non-empty
- `effect_class` must be one of `none|read|write`
- `default_timeout_s` must be a positive integer
- `input_schema` and `output_schema` must be objects
- `supports_idempotency_key` must be boolean
- `rate_limit` (if present) must be an object with positive integer values

## ToolCall contract
Executor calls tools via a ToolAdapter:
- invoke(tool_name, inputs, *, idempotency_key=None, timeout_s=None) -> ToolResult

ToolResult must include:
- ok: bool
- outputs: dict
- error: optional {code, message} — required when ok is False
- usage: optional {external_calls, tokens, bytes_in, bytes_out}
- metadata: optional (request_id, provider, etc.)

## validate_tool_call
Called before invoke. Signature: validate_tool_call(registry, tool_name, inputs, *, idempotency_key, retries, in_loop_body) -> dict (e.g. {"timeout_s": ...}).
- Resolve descriptor via registry.get(tool_name); unknown tool propagates KeyError.
- Validate inputs: must be a dict; in full implementation validate against descriptor.input_schema (e.g. jsonschema).
- If effect_class == "write" and (retries > 0 or in_loop_body): require idempotency_key is set and descriptor.supports_idempotency_key is True; else raise ToolContractError.
- Return dict with timeout_s from descriptor.default_timeout_s for caller to pass to invoke.

## validate_tool_result
Called after invoke when strict mode or in tests. Signature: validate_tool_result(desc, result, strict=False) -> None.
- If result.ok is False, result.error must be set; else raise ToolContractError ("tool result not ok but no error provided").
- In strict mode: validate result.outputs against descriptor.output_schema (e.g. jsonschema); raise on mismatch.

## Enforcement rules
At tool invocation:
- validate inputs against input_schema
- validate outputs against output_schema (in strict mode or tests)
- enforce effect_class and idempotency:
  - if tool.effect_class == write and retries enabled or in loop body:
    - require idempotency_key AND tool.supports_idempotency_key
- enforce timeout defaults
- enforce rate limits (MVP: simple token bucket per tool)

## Rate limiting
- ToolDescriptor.rate_limit: optional dict with e.g. requests_per_minute (int), burst (int).
- Enforcement: MVP simple token bucket per tool; before invoke, check/consume a token; on exceed either block (pause) or raise (error) depending on run policy or tool policy.
- Token bucket: refill at requests_per_minute/60 per second; capacity burst; one request consumes one token.

## Tool invocation events and usage
- After invoke, ToolResult.usage may contain external_calls, tokens, bytes_in, bytes_out (if adapter provides them).
- Dispatcher or executor should emit a tool_invocation event (e.g. to telemetry) with tool_name, ok, usage, so run_state/telemetry can aggregate and budgets can consume.
- Native adapter idempotency behavior: when `idempotency_key` is provided, successful outputs are persisted under `memory/automation/<session_target>/post_dedupe.json` in `entries[idempotency_key]`, and subsequent calls can return cached outputs with `metadata.dedupe_hit=true`.

## Planner integration
- When an optional ToolRegistry is passed to the planner, the planner may only emit tool nodes for registered tools: filter out (or reject) any tool node whose assigned_entity is not in the registry.
- Planner should copy tool.default_timeout_s and effect_class into node.policy for tool nodes unless the node already overrides them; when a registry is provided, use the descriptor for that tool for these defaults.

## Acceptance tests
- invalid input fails before invoke
- invalid output fails validation in strict mode
- write tool with retries but no idempotency_key rejected
- rate limiting triggers pause or error depending on policy
