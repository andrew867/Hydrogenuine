# Security and Privacy

Hydrogenuine Community defaults to local-only operation.

- Telemetry is off.
- The deterministic stub model uses no network.
- Tool execution is default-deny until a lease is approved.
- Memory has no action authority.
- Secrets must be supplied through local environment variables or private config files, not committed files.
- The public export gate blocks bytecode-only directories, cache artifacts, private filesystem paths and known private-edge markers.

Report vulnerabilities using `SECURITY.md`.
