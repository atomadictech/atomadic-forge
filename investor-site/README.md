# investor-site — invest.atomadic.tech

The interactive investor overview at <https://invest.atomadic.tech>. Renders the
full Atomadic ecosystem (Forge, Lang, AAAA-Nexus, sovereign agent + 8 surfaces)
in-page — no PDFs, every claim verifiable.

## Run locally

```bash
cd investor-site
npm install
npm run dev   # http://localhost:3000
```

## Build (static export)

```bash
npm run build   # next build --turbopack → out/
```

Output is fully static (`output: "export"` in `next.config.ts`). The `out/`
directory drops onto any static host.

## Deploy to Cloudflare Pages

This site lives as a subfolder inside `atomadictech/atomadic-forge`. Configure
the Cloudflare Pages project to build only this subfolder:

| Setting | Value |
|---|---|
| Production branch | `main` |
| Root directory | `investor-site` |
| Build command | `npm install && npm run build` |
| Build output directory | `out` |
| Node version | `20` |
| Custom domain | `invest.atomadic.tech` |

Once those settings are in place, every push to `main` that touches
`investor-site/**` rebuilds and deploys automatically.

## Why the path build uses `--turbopack`

The repo is at a Windows path containing `!!`, which the legacy webpack pipeline
rejects (it reserves `!` for loader syntax). Turbopack is unaffected. Cloudflare
Pages runs on Linux so the constraint is local-only — the build script keeps
`--turbopack` for both environments because Turbopack is also faster.

## Tech

- **Next.js 15** app-router with `output: "export"`
- **Tailwind CSS v4** via `@tailwindcss/postcss`
- **Motion** (Framer Motion) for animations
- **lucide-react** icons
- **JetBrains Mono** as the canonical typeface
- **No backend** — the page is pure static HTML/CSS/JS at runtime
