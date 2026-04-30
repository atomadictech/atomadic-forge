"""Tier a0 — Forge subscription gate constants and result types.

Golden Path Lane C W5 deliverable. Pairs with
``a1_at_functions/forge_auth.py`` (pure helpers — env parsing, request
shaping, hashing) and ``a2_mo_composites/forge_auth_client.py``
(stateful HTTP client + in-memory verify cache + offline-grace logic).
The MCP gate enforcing these constants lives at
``a3_og_features/mcp_server.py``; the ``forge login`` CLI verb that
captures the user's key lives at ``a4_sy_orchestration/login_cmd.py``.

Why this file exists at a0: the endpoints, env var name, key prefix,
cache TTL, and offline grace window are pure data — every tier above
must reference the SAME values, and a0 is the only place every tier is
allowed to import from. Putting them anywhere else would force either
an upward import or a duplicated literal.

Schema-version-style note: these are subscription-gate constants, not
wire-format constants — they don't carry a ``schema_version`` field.
But the ``VerifyResult`` and ``UsageLogResult`` TypedDicts ARE the
contract between a1's pure parsers and a2's stateful client; changing
their shape is a minor bump (additive optional field) or a major bump
(rename / required field) per AGENTS.md §4.
"""

from __future__ import annotations

from typing import TypedDict


# ---- endpoints ----------------------------------------------------------

DEFAULT_AUTH_ENDPOINT = "https://forge-auth.atomadic.tech/v1/forge/auth/verify"
"""Remote endpoint that verifies a user's ``fk_live_*`` API key.

Returns JSON shaped by ``VerifyResult`` (after a1 parsing). Operators
can override at runtime via the ``FORGE_AUTH_URL`` env var; tests
inject a fake by passing a different ``auth_endpoint`` to the a2
client constructor.
"""

DEFAULT_USAGE_ENDPOINT = "https://forge-auth.atomadic.tech/v1/forge/usage/log"
"""Fire-and-forget telemetry endpoint for per-tool-call usage logging.

The a2 client swallows every exception this endpoint can raise —
billing telemetry must NEVER block a paying user's tool execution.
"""


# ---- env / key shape ----------------------------------------------------

API_KEY_ENV = "FORGE_API_KEY"
"""Environment variable the MCP server reads on every dispatch.

Set by ``forge login`` (which writes to
``~/.atomadic-forge/credentials.toml``) or by the operator directly.
Empty / missing / wrong-prefix → MCP returns ``-32001`` for every
``tools/call``.
"""

API_KEY_PREFIX = "fk_live_"
"""Required prefix for a real Forge subscription key.

Test keys (``fk_test_*``) and obvious junk are rejected at the a1
shape-validator BEFORE we waste a round trip to the verify endpoint.
"""


# ---- caching / grace ----------------------------------------------------

VERIFY_CACHE_TTL_SECONDS = 300
"""How long a successful verify result stays cached in the a2 client.

5 minutes is the right balance: short enough that a key revoked at
the dashboard takes effect within one MCP session, long enough that
a coding agent firing 50+ ``tools/call`` requests per minute doesn't
hit the verify endpoint 50 times.
"""

OFFLINE_GRACE_SECONDS = 86400
"""Seconds since last successful verify during which we tolerate
unreachable verify endpoints.

If the user has a freshly-verified key and then drops to a flaky /
air-gapped network, we keep them productive for 24 hours under a
``degraded=True`` flag. Past 24h with no fresh verify → gate closes.
"""


# ---- result types -------------------------------------------------------

class VerifyResult(TypedDict, total=False):
    """Outcome of a single verify call (or its cached/degraded form).

    ``ok``         — True if the key is currently allowed to use the
                     MCP tools (success OR within-grace degraded mode).
    ``email``      — Email registered for the subscription.
    ``plan``       — Plan slug (``free``, ``starter``, ``pro``, ...).
    ``reason``     — Human-readable explanation (mostly used on ok=False).
    ``cached``     — True if served from the in-memory cache.
    ``degraded``   — True if verify endpoint was unreachable but we
                     served a within-grace last-known-good result.
    ``checked_at`` — Unix epoch seconds of the underlying verify call.
    """

    ok: bool
    email: str
    plan: str
    reason: str
    cached: bool
    degraded: bool
    checked_at: float


class UsageLogResult(TypedDict, total=False):
    """Outcome of a usage-log POST.

    Fire-and-forget by design — the a2 client returns this for tests
    and observability but NEVER raises and NEVER blocks the calling
    tool. Production callers should ignore the result.
    """

    sent: bool
    reason: str
