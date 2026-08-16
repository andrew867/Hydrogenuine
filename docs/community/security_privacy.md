# Security and Privacy

Hydrogenuine Community defaults to local-only operation.

- Telemetry is off.
- The deterministic stub model uses no network.
- Native demo and local-model gateway access is no-key and loopback-only.
- Local no-key mode is refused outside demo/development runtime labels.
- Tool execution is default-deny until a lease is approved.
- Memory has no action authority.
- Secrets must be supplied through local environment variables or private config files, not committed files.
- `hg init` stores provider key environment-variable names, never provider key values.
- The public export gate blocks bytecode-only directories, cache artifacts, private filesystem paths and known private-edge markers.

Report vulnerabilities using `SECURITY.md`.
