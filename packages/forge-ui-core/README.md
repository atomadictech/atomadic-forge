# @atomadic/forge-ui-core

Shared React UI core for Atomadic Forge. Powers both the Tauri desktop app
(`forge-studio`) and the Next.js PWA (`forge-web`) — they render the **exact
same components** and differ only in the `ForgeClient` they inject.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    @atomadic/forge-ui-core                   │
│                                                              │
│   ForgeShell  ←  Navigation, Scan, Graph, Heatmap, Debt,     │
│                  Topology, Settings, ErrorBanner, StatusPip  │
│        │                                                     │
│        ▼                                                     │
│   ForgeClient (interface)  ──  TauriForgeClient (Tauri IPC)  │
│                            ──  HttpForgeClient  (fetch /api) │
│                            ──  StubForgeClient  (dev/tests)  │
└──────────────────────────────────────────────────────────────┘
```

## Use it

```tsx
import "@atomadic/forge-ui-core/theme.css";
import { ForgeShell, TauriForgeClient } from "@atomadic/forge-ui-core";
import { invoke } from "@tauri-apps/api/core";

const client = new TauriForgeClient({ invoke });

export function App() {
  return <ForgeShell client={client} brand="FORGE STUDIO" />;
}
```

```tsx
// Web
import "@atomadic/forge-ui-core/theme.css";
import { ForgeShell, HttpForgeClient } from "@atomadic/forge-ui-core";

const client = new HttpForgeClient({ baseUrl: "/api/forge" });

export default function Page() {
  return <ForgeShell client={client} brand="FORGE WEB" />;
}
```

## Why a shared core

"Identical Tauri and PWA" is only achievable if there's one source of truth.
This package is that source: every screen, every state shape, every type
definition. Both apps are now thin shells responsible for one thing — supplying
a transport-flavored `ForgeClient`.

## Tailwind v4 requirement

Consumers must load Tailwind v4. The `theme.css` file declares `@theme { … }`
tokens consumed by all components. Importing the CSS once is enough.
