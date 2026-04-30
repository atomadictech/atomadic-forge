# forge-web — Atomadic Forge PWA

The web/PWA shell for [Atomadic Forge](../). Renders the **same UI** as the
desktop app (`forge-studio`) by importing `@atomadic/forge-ui-core` and
injecting an HTTP-flavored `ForgeClient`.

## Run

```bash
pnpm install            # at monorepo root
pnpm --filter forge-web dev
```

Open <http://localhost:3000>. The PWA install prompt appears on supported
browsers; once installed the app runs offline-shell from the service worker.

## Backend

API routes under `app/api/forge/*` invoke the Atomadic Forge CLI via
`lib/forge-runner.ts`. Set `FORGE_BIN` to override the binary path; the default
is `python -m atomadic_forge`.

## Architecture

```
forge-web/                Next.js 15 PWA shell
├── app/
│   ├── ForgeApp.tsx     Mounts <ForgeShell client={httpClient} />
│   ├── layout.tsx        Manifest, theme color, viewport
│   ├── page.tsx          The single page — Forge has no routing today
│   ├── globals.css       Tailwind v4 + theme tokens
│   └── api/forge/        Subprocess proxy to forge CLI
└── public/
    ├── manifest.webmanifest
    └── sw.js             Offline shell + asset cache
```

All visual logic lives in [`@atomadic/forge-ui-core`](../packages/forge-ui-core).
This shell is intentionally tiny.
