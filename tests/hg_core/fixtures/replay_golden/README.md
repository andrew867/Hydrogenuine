# Golden DAG recordings for replay regression

This directory holds baseline recordings (attempts.jsonl) for a small set of deterministic golden DAGs. They are used to detect regressions: if executor or recording semantics change, re-running the golden DAGs will produce different digests.

## Layout

- `<dag_id>/attempts.jsonl` — one file per golden DAG, produced by running that DAG with the live dispatcher and recorder.

## How to record (update fixtures)

From the workspace root:

```powershell
python scripts/run_replay_regression.py --record
```

This runs each golden DAG with recording and writes `attempts.jsonl` into the corresponding `<dag_id>/` directory. Commit the changed files after verifying replay still matches (run the script without `--record` to compare).

## How to compare (regression check)

From the workspace root:

```powershell
python scripts/run_replay_regression.py
```

or:

```powershell
python scripts/run_replay_regression.py --compare
```

The script runs each golden DAG with recording, extracts request/response digests from the new run, and compares them to the digests in the fixture files. If any digest differs, the script exits with code 1 and prints which DAG and attempt differ. Use in CI or before releases to ensure no unintended change to recording or execution semantics.

## Golden DAGs

Defined in `scripts/run_replay_regression.py`:

- `golden_linear_2` — two eval nodes in sequence (a -> b).
- `golden_linear_3` — three eval nodes in sequence (a -> b -> c).

All use eval-only nodes so runs are deterministic and do not call external tools or LLMs.
