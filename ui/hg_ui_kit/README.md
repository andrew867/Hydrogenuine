# hg_ui_kit

Shared Hydrogenuine design system consumed by `client_ui`, `operator_console/ui`, and `product_console/ui`.

## Install (per app)

```json
"dependencies": {
  "hg_ui_kit": "file:../../ui/hg_ui_kit"
}
```

```bash
cd ui/hg_ui_kit && npm install && npm run build
```

## Usage

```tsx
import "hg_ui_kit/tokens.css";
import "hg_ui_kit/components.css";
import { ThemeProvider, EnvBadge, Button } from "hg_ui_kit";

<ThemeProvider defaultMode="dark" defaultDensity="compact">
  <EnvBadge env="dev" mode="shadow" />
  <Button variant="primary">Run</Button>
</ThemeProvider>
```

## Scripts

- `npm run build` — TypeScript declarations + Vite library bundle
- `npm test` — Vitest (U-K1..U-K8)

## Docs

- `docs/microcopy.md` — error/empty/destructive copy table
- `docs/testids.md` — `data-testid` conventions
