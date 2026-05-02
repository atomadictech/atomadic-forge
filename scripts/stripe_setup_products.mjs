#!/usr/bin/env node
/**
 * Atomadic Forge — Stripe product setup
 *
 * One-shot script: creates the 12 v4 products + prices in your Stripe
 * account, then writes the resulting price IDs to:
 *
 *    docs/STRIPE_PRICE_IDS.json    (machine-readable, gitignored)
 *
 * AND patches them directly into:
 *
 *    ../atomadic-forge-site/functions/api/checkout.ts
 *
 * Usage:
 *    $env:STRIPE_SECRET_KEY = "sk_test_..."   # PowerShell
 *    export STRIPE_SECRET_KEY=sk_test_...     # bash/zsh
 *    node scripts/stripe_setup_products.mjs
 *
 * Idempotent: re-runs reuse existing products by `metadata.atomadic_slug`.
 */

import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SITE_CHECKOUT = resolve(ROOT, "..", "..", "Users", "atoma", "atomadic-forge-site", "functions", "api", "checkout.ts");
// Fallback: try the canonical Windows path the user has
const SITE_CHECKOUT_FALLBACK = "C:/Users/atoma/atomadic-forge-site/functions/api/checkout.ts";

// Auto-load from the master VAULT.env if STRIPE_SECRET_KEY isn't already
// in the environment. The vault is the canonical home for ecosystem keys
// per the May 2026 reorg.
function loadFromVault() {
  const VAULTS = [
    "C:/!!AtomadicStandard/VAULT.env",
    process.env.HOME ? `${process.env.HOME}/.atomadic/.env` : null,
    process.env.USERPROFILE ? `${process.env.USERPROFILE}/.atomadic/.env` : null,
  ].filter(Boolean);
  for (const p of VAULTS) {
    if (!existsSync(p)) continue;
    const text = readFileSync(p, "utf-8");
    for (const line of text.split(/\r?\n/)) {
      const m = line.match(/^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
      if (!m) continue;
      const [, k, vRaw] = m;
      if (k.startsWith("#")) continue;
      const v = vRaw.replace(/^['"]|['"]$/g, "");
      if (v && !process.env[k]) process.env[k] = v;
    }
    if (process.env.STRIPE_SECRET_KEY) {
      console.log(`📒 Loaded STRIPE_SECRET_KEY from ${p}`);
      return;
    }
  }
}
loadFromVault();

const KEY = process.env.STRIPE_SECRET_KEY;
if (!KEY || !KEY.startsWith("sk_")) {
  console.error("ERROR: STRIPE_SECRET_KEY not found.");
  console.error("Searched:");
  console.error("  • C:/!!AtomadicStandard/VAULT.env");
  console.error("  • $HOME/.atomadic/.env");
  console.error("  • process env");
  console.error("");
  console.error("Add `STRIPE_SECRET_KEY=sk_...` to one of those files, or set it via:");
  console.error("PowerShell:  $env:STRIPE_SECRET_KEY = 'sk_test_...'");
  console.error("Bash:        export STRIPE_SECRET_KEY=sk_test_...");
  process.exit(1);
}

const MODE = KEY.startsWith("sk_live_") ? "LIVE" : "TEST";
console.log(`\n🔑 Stripe mode: ${MODE}\n`);

// ─── Product catalogue ───────────────────────────────────────────────

const SUBSCRIPTIONS = [
  { slug: "basic_monthly",  name: "Forge Standard Basic (monthly)",  cents: 1900,   interval: "month" },
  { slug: "basic_yearly",   name: "Forge Standard Basic (yearly)",   cents: 19000,  interval: "year"  },
  { slug: "dev_monthly",    name: "Forge Standard Dev (monthly)",    cents: 3900,   interval: "month" },
  { slug: "dev_yearly",     name: "Forge Standard Dev (yearly)",     cents: 39000,  interval: "year"  },
  { slug: "pro_monthly",    name: "Forge Standard Pro (monthly)",    cents: 9900,   interval: "month" },
  { slug: "pro_yearly",     name: "Forge Standard Pro (yearly)",     cents: 99000,  interval: "year"  },
  { slug: "enterprise_monthly", name: "Forge Standard Enterprise (monthly)", cents: 250000, interval: "month" },
];

const ONE_TIMES = [
  { slug: "founder_lifetime",     name: "Atomadic Lifetime Founder",     cents: 99900,  product_type: "forge_founder_lifetime", credits: 0 },
  { slug: "credits_starter",      name: "Forge Credits — Starter",       cents: 2500,   product_type: "forge_credit_pack",       credits: 3000  },
  { slug: "credits_builder",      name: "Forge Credits — Builder",       cents: 10000,  product_type: "forge_credit_pack",       credits: 15000 },
  { slug: "credits_team",         name: "Forge Credits — Team",          cents: 50000,  product_type: "forge_credit_pack",       credits: 100000 },
  { slug: "credits_enterprise",   name: "Forge Credits — Enterprise",    cents: 250000, product_type: "forge_credit_pack",       credits: 600000 },
];

// ─── Stripe API helpers ──────────────────────────────────────────────

const STRIPE_BASE = "https://api.stripe.com/v1";

async function stripeReq(path, params = {}) {
  const body = new URLSearchParams();
  function add(prefix, val) {
    if (val === null || val === undefined) return;
    if (typeof val === "object" && !Array.isArray(val)) {
      for (const [k, v] of Object.entries(val)) add(`${prefix}[${k}]`, v);
    } else if (Array.isArray(val)) {
      val.forEach((v, i) => add(`${prefix}[${i}]`, v));
    } else {
      body.append(prefix, String(val));
    }
  }
  for (const [k, v] of Object.entries(params)) add(k, v);

  const res = await fetch(`${STRIPE_BASE}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${KEY}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Stripe ${path} ${res.status}: ${errText}`);
  }
  return res.json();
}

async function stripeGet(path) {
  const res = await fetch(`${STRIPE_BASE}${path}`, {
    headers: { Authorization: `Bearer ${KEY}` },
  });
  if (!res.ok) throw new Error(`Stripe GET ${path} ${res.status}`);
  return res.json();
}

// ─── Idempotent product lookup ───────────────────────────────────────

async function findProductBySlug(slug) {
  const url = `/products/search?query=${encodeURIComponent(`metadata['atomadic_slug']:'${slug}'`)}&limit=1`;
  const r = await stripeGet(url);
  return r.data?.[0] || null;
}

async function findActivePriceForProduct(productId) {
  const r = await stripeGet(`/prices?product=${productId}&active=true&limit=1`);
  return r.data?.[0] || null;
}

// ─── Per-SKU upsert ──────────────────────────────────────────────────

async function upsertSubscription(sku) {
  console.log(`→ ${sku.slug.padEnd(24)} ($${(sku.cents / 100).toFixed(2)} ${sku.interval})`);
  let product = await findProductBySlug(sku.slug);
  if (!product) {
    product = await stripeReq("/products", {
      name: sku.name,
      metadata: {
        atomadic_slug: sku.slug,
        product_type: "forge_subscription",
      },
    });
    console.log(`   product: ${product.id} (created)`);
  } else {
    console.log(`   product: ${product.id} (exists)`);
  }
  let price = await findActivePriceForProduct(product.id);
  if (!price || price.unit_amount !== sku.cents || price.recurring?.interval !== sku.interval) {
    price = await stripeReq("/prices", {
      product: product.id,
      unit_amount: sku.cents,
      currency: "usd",
      recurring: { interval: sku.interval },
      metadata: { atomadic_slug: sku.slug },
    });
    console.log(`   price:   ${price.id} (created)`);
  } else {
    console.log(`   price:   ${price.id} (exists)`);
  }
  return { slug: sku.slug, product_id: product.id, price_id: price.id, cents: sku.cents, interval: sku.interval };
}

async function upsertOneTime(sku) {
  console.log(`→ ${sku.slug.padEnd(24)} ($${(sku.cents / 100).toFixed(2)} one-time)`);
  let product = await findProductBySlug(sku.slug);
  const productMeta = {
    atomadic_slug: sku.slug,
    product_type: sku.product_type,
  };
  if (sku.credits) productMeta.credits = String(sku.credits);

  if (!product) {
    product = await stripeReq("/products", {
      name: sku.name,
      metadata: productMeta,
    });
    console.log(`   product: ${product.id} (created)`);
  } else {
    console.log(`   product: ${product.id} (exists)`);
  }
  let price = await findActivePriceForProduct(product.id);
  if (!price || price.unit_amount !== sku.cents || price.type !== "one_time") {
    price = await stripeReq("/prices", {
      product: product.id,
      unit_amount: sku.cents,
      currency: "usd",
      metadata: { atomadic_slug: sku.slug },
    });
    console.log(`   price:   ${price.id} (created)`);
  } else {
    console.log(`   price:   ${price.id} (exists)`);
  }
  return { slug: sku.slug, product_id: product.id, price_id: price.id, cents: sku.cents };
}

// ─── Main ────────────────────────────────────────────────────────────

async function main() {
  const result = { mode: MODE, generated_at: new Date().toISOString(), subscriptions: [], one_time: [] };

  console.log("📦 Subscriptions");
  for (const sku of SUBSCRIPTIONS) {
    result.subscriptions.push(await upsertSubscription(sku));
  }

  console.log("\n📦 One-time products");
  for (const sku of ONE_TIMES) {
    result.one_time.push(await upsertOneTime(sku));
  }

  // ─── Write the JSON ledger ─────────────────────────────────────────
  const ledgerPath = join(ROOT, "docs", "STRIPE_PRICE_IDS.json");
  writeFileSync(ledgerPath, JSON.stringify(result, null, 2) + "\n", "utf-8");
  console.log(`\n💾 Wrote ${ledgerPath}`);

  // ─── Patch checkout.ts ─────────────────────────────────────────────
  const checkoutPath = existsSync(SITE_CHECKOUT) ? SITE_CHECKOUT : SITE_CHECKOUT_FALLBACK;
  if (!existsSync(checkoutPath)) {
    console.warn(`⚠ Could not locate checkout.ts at ${checkoutPath}; skipping patch.`);
    console.warn("   Hand-edit checkout.ts using the IDs in STRIPE_PRICE_IDS.json.");
    return;
  }

  let src = readFileSync(checkoutPath, "utf-8");

  const subBySlug = Object.fromEntries(result.subscriptions.map(s => [s.slug, s.price_id]));
  const oneBySlug = Object.fromEntries(result.one_time.map(s => [s.slug, s.price_id]));

  const subs = ["basic", "dev", "pro", "enterprise"];
  for (const t of subs) {
    if (subBySlug[`${t}_monthly`]) {
      src = src.replace(
        new RegExp(`"price_TODO_${t}_monthly_\\d+"`, "g"),
        `"${subBySlug[`${t}_monthly`]}"`,
      );
    }
    if (subBySlug[`${t}_yearly`]) {
      src = src.replace(
        new RegExp(`"price_TODO_${t}_yearly_\\d+"`, "g"),
        `"${subBySlug[`${t}_yearly`]}"`,
      );
    }
  }

  if (oneBySlug["founder_lifetime"]) {
    src = src.replace(
      /"price_TODO_founder_lifetime_999"/g,
      `"${oneBySlug["founder_lifetime"]}"`,
    );
  }
  for (const pack of ["starter", "builder", "team", "enterprise"]) {
    const id = oneBySlug[`credits_${pack}`];
    if (id) {
      src = src.replace(
        new RegExp(`"price_TODO_credits_${pack}_\\d+"`, "g"),
        `"${id}"`,
      );
    }
  }

  writeFileSync(checkoutPath, src, "utf-8");
  console.log(`✓ Patched ${checkoutPath} with real Stripe price IDs`);

  console.log("\n──────────────────────────────────────────────────");
  console.log("✓ Done. Next:");
  console.log("    1. cd C:/Users/atoma/atomadic-forge-site && npm run deploy");
  console.log("    2. Test a checkout via the live /pricing page");
  console.log("    3. Commit STRIPE_PRICE_IDS.json (or .gitignore it if you prefer)");
  console.log("──────────────────────────────────────────────────\n");
}

main().catch((e) => {
  console.error("\n❌ ERROR:", e.message);
  process.exit(1);
});
