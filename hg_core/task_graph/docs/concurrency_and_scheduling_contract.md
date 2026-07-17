# Concurrency and scheduling contract (Autonomy Ch1 Phase 5)

Contract for Q1 (distributed locking), Q2 (concurrency caps), Q3 (jitter), Q4 (priority and load shedding). Prevents duplicate runs and thundering herds; enforces concurrency limits.

## Q1. Distributed locking

Before running a workflow:

- **Acquire lock** for (workflow_id, time_bucket).
- **Lock TTL** covers expected run time + buffer.
- **On completion**, release lock.

**Acceptance:** Concurrent triggers for same (workflow_id, time_bucket) result in at most one run.

See [SCHEDULING_CONCURRENCY](docs/automation/SCHEDULING_CONCURRENCY.md).

## Q2. Concurrency caps

Enforce:

- **Global** max concurrent workflows.
- **Per-workflow** max concurrent runs.
- **Per-destination** max concurrent side effects (optional).

**Acceptance:** When at cap, new runs are rejected or queued.

## Q3. Jitter

Scheduled triggers apply **jitter** to start times to avoid spikes (e.g. ±N minutes random delay per task).

**Acceptance:** Schedules are spread; no thundering herd at exact minute.

## Q4. Priority and load shedding

Define workflow **priorities**. When under load:

- Drop or delay **low priority** workflows first.
- Keep **health checks** and **alerts** running.

**Acceptance:** System remains stable under load; high-priority work continues.
