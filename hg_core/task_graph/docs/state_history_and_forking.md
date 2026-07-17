# State History and Forking

Within run_dir:
- state_history/state_000001.json, state_000002.json, ...
- state_history/index.jsonl (append-only)
- state_history/state_latest.json convenience copy

Index entry:
{ seq, ts, event_idx?, node_id?, reason, state_path }

Fork:
- copy state_<seq>.json into new run_dir/state.json
- set run_id to new id
- resume new run_id continues independently
