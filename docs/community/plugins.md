# Plugins and Extensions

Community extensions should be small, auditable adapters. They must not bypass governance.

Minimum contract:

1. Declare the capability name.
2. Accept explicit input only.
3. Return structured output and artifacts.
4. Require a lease before performing side effects.
5. Emit or request a receipt for executed work.

See `examples/plugins/echo_plugin.py` for a minimal adapter.
