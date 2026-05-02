# Stripe Setup Handoff — Pricing v4 Launch

Everything that requires your hands (Stripe dashboard, DNS, Discord
invites). All code is shipped; this is the manual config layer.

Estimated time: **30 minutes** if you have Stripe + Cloudflare access.

---

## 1. Stripe products to create

The site references these Stripe price IDs via env vars + hardcoded fallbacks
in `atomadic-forge-site/functions/api/checkout.ts`. You need to mint each one
in **Stripe Dashboard → Products** and either (a) update the fallbacks in
`checkout.ts` with the real `price_*` IDs, or (b) set them as env vars in the
Cloudflare Pages project.

### Subscriptions (recurring)

| Product name | Price | Billing | Slug used in checkout body |
|---|---|---|---|
| Forge Standard Basic (monthly) | **$19/mo** | recurring monthly | `tier=basic, billing=monthly` |
| Forge Standard Basic (yearly) | **$190/yr** | recurring yearly | `tier=basic, billing=yearly` |
| Forge Standard Dev (monthly) | **$39/mo** | recurring monthly | `tier=dev, billing=monthly` |
| Forge Standard Dev (yearly) | **$390/yr** | recurring yearly | `tier=dev, billing=yearly` |
| Forge Standard Pro (monthly) | **$99/mo** *(per-seat metering)* | recurring monthly | `tier=pro, billing=monthly` |
| Forge Standard Pro (yearly) | **$990/yr** *(per-seat metering)* | recurring yearly | `tier=pro, billing=yearly` |
| Forge Standard Enterprise | **$2,500/mo** *(custom contract)* | recurring monthly | `tier=enterprise` |

### One-time payments

| Product name | Price | Mode | Slug used |
|---|---|---|---|
| **Atomadic Lifetime Founder** | **$999** | one-time | `mode=founder` |
| Forge Credits — Starter | $25 | one-time | `mode=credits, pack=starter` |
| Forge Credits — Builder | $100 | one-time | `mode=credits, pack=builder` |
| Forge Credits — Team | $500 | one-time | `mode=credits, pack=team` |
| Forge Credits — Enterprise | $2,500 | one-time | `mode=credits, pack=enterprise` |
| Forge One-Time Refactor | $499 | one-time | `mode=buy` *(legacy, kept)* |

### For each Stripe product, set this metadata:

```
product_type = forge_subscription   (for recurring)
            OR forge_founder_lifetime  (for $999 founder)
            OR forge_credit_pack       (for credit packs)
            OR forge_one_time_refactor (legacy)

For credit packs, also set:
   credits = 3000   (for Starter)
   credits = 15000  (for Builder)
   credits = 100000 (for Team)
   credits = 600000 (for Enterprise)
```

The `forge-auth-worker`'s `stripe-webhook.ts` reads `metadata.product_type` to
decide what to mint.

### Update price IDs

After creating each product, copy the `price_*` ID and either:

**Option A (fastest)** — edit `atomadic-forge-site/functions/api/checkout.ts`,
replace the `price_TODO_*` fallbacks with the real IDs. Commit + redeploy
Cloudflare Pages.

**Option B (cleanest)** — set env vars in **Cloudflare Pages → forge-atomadic-tech-site → Settings → Environment Variables**:

```
FORGE_PRICE_BASIC_MONTHLY      = price_xxx
FORGE_PRICE_BASIC_YEARLY       = price_xxx
FORGE_PRICE_DEV_MONTHLY        = price_xxx
FORGE_PRICE_DEV_YEARLY         = price_xxx
FORGE_PRICE_PRO_MONTHLY        = price_xxx
FORGE_PRICE_PRO_YEARLY         = price_xxx
FORGE_PRICE_ENTERPRISE_MONTHLY = price_xxx
FORGE_PRICE_FOUNDER_LIFETIME   = price_xxx
FORGE_PRICE_CREDITS_STARTER    = price_xxx
FORGE_PRICE_CREDITS_BUILDER    = price_xxx
FORGE_PRICE_CREDITS_TEAM       = price_xxx
FORGE_PRICE_CREDITS_ENTERPRISE = price_xxx
```

Then update `checkout.ts` to read from `ctx.env.FORGE_PRICE_*` first and fall
back to the hardcoded values. (10-line edit; can be a follow-up commit.)

---

## 2. Stripe webhook configuration

The forge-auth-worker (`forge-auth.atomadic.tech`) listens at `/v1/forge/stripe/webhook`.

### Configure in Stripe Dashboard

1. **Developers → Webhooks → Add endpoint**
2. Endpoint URL: `https://forge-auth.atomadic.tech/v1/forge/stripe/webhook`
3. Listen to events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - **`checkout.session.completed`** ← NEW, handles Founder + credits
4. Copy the signing secret (starts with `whsec_`).

### Set the secret on the worker

```powershell
cd C:\!!AtomadicStandard\forge-auth-worker
npx wrangler secret put STRIPE_WEBHOOK_SECRET
# paste the whsec_ value when prompted
```

If it's already set from a previous webhook, **you must update it** —
adding the `checkout.session.completed` event likely caused Stripe to
re-issue the secret.

### Re-deploy the worker

```powershell
cd C:\!!AtomadicStandard\forge-auth-worker
npx wrangler deploy
```

This ships the new webhook handler that mints Founder keys.

---

## 3. Test the flow end-to-end

Stripe has a **test mode** with fake cards (`4242 4242 4242 4242`, any
future date, any CVC). Use it first.

### Test 1 — Standard subscription

1. Go to https://forge.atomadic.tech/pricing
2. Click "Subscribe — $19/mo" on Basic
3. Enter `test@example.com`
4. Complete Stripe checkout with `4242 4242 4242 4242`
5. **Expected:** Stripe sends `customer.subscription.created` to the
   webhook → forge-auth-worker mints `fk_live_*` key → Resend emails it
   to `test@example.com` → user redirected to `/account?session_id=cs_test_*`
6. **Verify:** the account page shows the new key with `plan: basic_monthly`

### Test 2 — Founder's Pack

1. Go to https://forge.atomadic.tech/pricing
2. Click "Claim Founder #" on the Founder's Pack hero
3. Enter `founder-test@example.com`
4. Complete Stripe checkout with `4242 4242 4242 4242`
5. **Expected:** Stripe sends `checkout.session.completed` to the webhook
   → forge-auth-worker counts existing `forge_founder_lifetime` keys → mints
   `ak_master_*` key (numbered F001..F025) → emails it
6. **Verify:** D1 query returns 1 row:
   ```bash
   npx wrangler d1 execute forge_auth_db --command "SELECT plan, status, email FROM forge_keys WHERE plan='forge_founder_lifetime'"
   ```

### Test 3 — Credit pack

1. Click "Buy $25" on the Starter credit pack
2. Enter `credits-test@example.com`
3. Complete with test card
4. **Expected:** webhook logs `Credit pack purchased: ... +3000 (starter)`
5. **NOTE:** the credit ledger isn't fully wired yet. Logs are present;
   the actual balance display in `/account` is a Phase-2 feature.

### Test 4 — Hosted MCP works with the issued key

```bash
curl -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer fk_live_<ISSUED_KEY>" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  https://forge.atomadic.tech/mcp
```

Should return 29 tools.

### Test 5 — Founder key works on Deluxe MCP

```bash
curl -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer ak_master_<FOUNDER_KEY>" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  https://forge.atomadic.tech/deluxe/mcp
```

Should return 29 tools (same catalog as Standard until Deluxe gets
exclusive tools, but the auth gate works).

---

## 4. Going live (production mode)

Stripe → Switch to live mode. Repeat product creation in live mode.

Update the `STRIPE_API_KEY` secret on `forge-auth-worker`:

```powershell
cd C:\!!AtomadicStandard\forge-auth-worker
npx wrangler secret put STRIPE_API_KEY
# paste your sk_live_ key
```

And the webhook signing secret (live mode webhooks have their own
`whsec_*`):

```powershell
npx wrangler secret put STRIPE_WEBHOOK_SECRET
```

Re-deploy:

```powershell
npx wrangler deploy
```

---

## 5. Founders Discord setup

When the first Founder buys, they need an invite. Easiest path:

1. Create a Discord server "Atomadic Founders" (or use your existing
   Atomadic Discord with a private "founders" channel).
2. Generate a one-time invite link, never-expire, max-uses 25:
   `https://discord.gg/<your-invite-code>`
3. Add the invite link to the welcome email template in
   `forge-auth-worker/src/lib/email.ts`. Search for the `ak_master_`
   email template and inject the invite link in the founder welcome
   copy. (One-line change.)

---

## 6. Launch announcement copy

Once Stripe products are live + Test 2 above passes, you're ready to
announce. Suggested channels:

### Hacker News (Show HN)

> **Show HN: Atomadic Forge — Architecture-as-a-service for AI coding agents
> ($999 lifetime founder spots, first 25)**
>
> Forge is a 29-tool MCP server that gives any coding agent (Cursor, Claude
> Code, Aider, Devin) a normative 5-tier monadic architecture law. Drop the
> URL into your `mcp.json`, get signed receipts on every emit, attest
> conformance against EU AI Act / SR 11-7 / FDA PCCP / CMMC-AI.
>
> Launching with a Founder's Pack — first 25 buyers get $999 lifetime
> access to the entire Atomadic ecosystem (Forge Standard, Forge Deluxe
> when it launches, AAAA-Nexus, every future product). Numbered keys
> F001–F025.
>
> Live: https://forge.atomadic.tech/pricing
> GitHub (BSL-1.1): https://github.com/atomadictech/atomadic-forge
> MCP URL: https://forge.atomadic.tech/mcp

### X / Twitter

> **Atomadic Forge is live.** 🛠
>
> Architecture-as-a-service for AI coding agents. 29 MCP tools.
> Signed receipts. Compliance attestations. From $19/mo.
>
> 👑 First 25 buyers: $999 lifetime everything.
>
> https://forge.atomadic.tech/pricing

### Discord / community

Pin a single message linking to /pricing with a 1-line summary of the
Founder's Pack scarcity.

---

## 7. What's NOT in this launch (Phase 2)

These are intentionally held back until the Deluxe catalog has 5+
exclusive tools beyond Standard:

- Deluxe tier ladder publicly listed (currently functional at
  `/deluxe/mcp` but not advertised)
- Deluxe Master Founder tier ($499) and Forge 5-Year Pack ($799)
- Volume / per-seat enterprise pricing UI
- Credit ledger UI in `/account`
- Stripe Customer Portal embed (subscription management self-service)

---

## Questions

If anything in this handoff is unclear, the relevant code is in:

- `atomadic-forge-site/functions/api/checkout.ts` — Stripe session creation
- `forge-auth-worker/src/routes/stripe-webhook.ts` — webhook event handlers
- `forge-auth-worker/src/lib/keys.ts` — API key generation
- `atomadic-forge-cloudflare-workers/mcp/src/a2_mo_composites/forge_auth.ts` — MCP-side auth check

Verdict: **PASS** once Stripe products are minted and Test 1 + Test 2 above
both pass.
