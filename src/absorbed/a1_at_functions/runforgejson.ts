/**
 * Server-side helper that invokes the Atomadic Forge CLI as a subprocess
 * and parses its `--json` output. Used by /api/forge/* routes.
 *
 * Prefers a long-running `forge mcp serve` MCP session (Phase 2 work) but
 * for Phase 1 falls back to one-shot CLI calls — robust, simple, slow-ish.
 */
import { spawn } from "node:child_process";

export interface ForgeRunOptions {
  /** Working directory. Defaults to process.cwd(). */
  cwd?: string;
  /** Extra env vars merged onto process.env. */
  env?: Record<string, string>;
  /** Timeout in ms. Default 60_000. */
  timeoutMs?: number;
}

export interface ForgeRunResult {
  ok: boolean;
  exitCode: number;
  stdout: string;
  stderr: string;
}

/** Locate the `forge` binary. Defaults to `python -m atomadic_forge`. */
function forgeArgv(args: string[]): { cmd: string; argv: string[] } {
  if (process.env.FORGE_BIN) {
    return { cmd: process.env.FORGE_BIN, argv: args };
  }
  return { cmd: "python", argv: ["-m", "atomadic_forge", ...args] };
}

export function runForge(args: string[], opts: ForgeRunOptions = {}): Promise<ForgeRunResult> {
  const { cmd, argv } = forgeArgv(args);
  const timeoutMs = opts.timeoutMs ?? 60_000;
  return new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    const child = spawn(cmd, argv, {
      cwd: opts.cwd,
      env: { ...process.env, ...(opts.env ?? {}) },
      shell: false,
    });
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      resolve({ ok: false, exitCode: -1, stdout, stderr: stderr + "\n[forge-runner] timeout" });
    }, timeoutMs);
    child.stdout.on("data", (b) => (stdout += b.toString()));
    child.stderr.on("data", (b) => (stderr += b.toString()));
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ ok: false, exitCode: -1, stdout, stderr: stderr + String(err) });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ ok: code === 0, exitCode: code ?? -1, stdout, stderr });
    });
  });
}

export async function runForgeJson<T = unknown>(
  args: string[],
  opts: ForgeRunOptions = {},
): Promise<T> {
  const r = await runForge([...args, "--json"], opts);
  if (!r.ok) {
    throw new Error(`forge ${args.join(" ")} failed (exit ${r.exitCode}): ${r.stderr.trim()}`);
  }
  try {
    return JSON.parse(r.stdout) as T;
  } catch (err) {
    throw new Error(`forge ${args.join(" ")} output not JSON: ${err}\n---STDOUT---\n${r.stdout}`);
  }
}
