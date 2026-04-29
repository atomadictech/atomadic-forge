# Security Policy

## Supported Versions

Forge is pre-1.0. Security fixes target the current `main` branch and the
latest tagged release when one exists.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Use GitHub private vulnerability reporting:

https://github.com/atomadictech/atomadic-forge/security/advisories/new

Include:

- A short impact summary.
- Reproduction steps or a minimal proof of concept.
- Affected versions, commit SHAs, or command invocations.
- Whether secrets, generated code, provider calls, or local model output are involved.

We will acknowledge valid reports as quickly as possible and coordinate a
fix before public disclosure.

## Secrets

Forge commands can call external AI providers. Never commit API keys,
`.env` files, transcript logs containing secrets, or generated outputs that
embed credentials. The chat context packer skips obvious secret files, but
operators are still responsible for reviewing what they send to a provider.
