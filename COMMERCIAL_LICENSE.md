# Commercial License — Atomadic Forge

Atomadic Forge is licensed under [Business Source License 1.1](LICENSE).

Under BSL-1.1:

- **Free** for non-commercial and open-source use
- **Free** for personal projects and individual developers
- **Free** for evaluation in any commercial context
- **Requires a commercial license** for production use inside a for-profit
  organization or as part of a commercial product

The license auto-converts to **Apache 2.0** on **2030-04-27** (the Change Date).

## Who needs a commercial license

You need a commercial license if your organization:

- Ships a commercial product that includes Forge or Forge-derived analyses
- Runs Forge in CI/CD as part of a paid SaaS, paid agent, or paid IDE plugin
- Hosts Forge for paying customers
- Is a Fortune-1000 / public-company subsidiary using Forge in production

You do **not** need a commercial license to:

- Run Forge on your own personal repositories
- Use Forge in OSS contributions
- Evaluate Forge before purchase
- Use the hosted MCP at `forge.atomadic.tech/mcp` (the hosted endpoint is
  governed by your subscription tier, not the BSL)

## How to buy

Three paths, pick the one that matches your usage:

### 1. Subscription — pay for the hosted MCP at `forge.atomadic.tech/mcp`

Subscribing to **Forge Standard Pro ($99/user/mo) or higher** automatically
includes a commercial license valid for the duration of your subscription.

See [forge.atomadic.tech/pricing](https://forge.atomadic.tech/pricing).

### 2. Atomadic Lifetime Founder — $999 one-time, first 25 only

The Founder's Pack includes a perpetual commercial license for Forge
Standard, Forge Deluxe (when launched), AAAA-Nexus, and every future
Atomadic product. One key, every product, forever.

See [forge.atomadic.tech/pricing#founder](https://forge.atomadic.tech/pricing).

### 3. Enterprise license

Custom annual contract starting at $2,500/mo. Includes:

- BSL commercial license, perpetual term
- SSO / audit logs / RBAC
- Self-hosted MCP option
- 99.9% SLA + dedicated Customer Success Manager
- Volume seat pricing

Contact: **hello@atomadic.tech** with subject "Forge Enterprise"

## Compliance attestation

Forge Standard Pro and above sign every receipt under your commercial
license. The signed receipt + your tier badge is auditable proof of
license compliance for your procurement team. Run:

```bash
forge certify . --emit-receipt out/receipt.json --sign
```

The receipt's `signatures.aaaa_nexus.commercial = true` field proves a
valid commercial license was active at signing time.

## Common questions

**Do I need a license to use the free CLI in my open-source project?**
No. BSL non-commercial use covers OSS contributions.

**Do I need a license to evaluate Forge?**
No. Evaluation is always free.

**Does the hosted MCP at forge.atomadic.tech/mcp require a commercial license?**
The hosted MCP is governed by your subscription tier. Free / Basic / Dev
tiers cover non-commercial and small-team use. Pro and Enterprise tiers
include commercial license rights.

**What happens if I'm using Forge commercially without a license?**
Email us at hello@atomadic.tech. The first conversation is always about
sizing the right plan, not enforcement. We're a small team — we'd rather
have you as a paying customer than a legal headache.

**Can I get a commercial license without using the hosted MCP?**
Yes — Enterprise plans include a perpetual commercial license valid for
self-hosted deployments. Contact hello@atomadic.tech.

---

The full BSL 1.1 text is at: <https://mariadb.com/bsl11/>

For questions about this commercial license, email **hello@atomadic.tech**.
