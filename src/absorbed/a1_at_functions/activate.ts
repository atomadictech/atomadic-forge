// Atomadic Forge — VS Code extension entry point.
//
// Spins up `forge lsp serve` as the language server for `.forge`
// sidecar files. The Python LSP (a3/lsp_server.py + a1/lsp_protocol.py)
// owns all the actual logic — diagnostics, hover, goto-source — so
// this extension stays a thin wrapper.
//
// Reconnect path:
//   1. activate() reads atomadicForge.serverPath + serverArgs
//   2. Spawns the server with stdio framing
//   3. Registers it for documents with languageId="forge" or files
//      whose name matches the `.forge` glob
//
// Restart path:
//   command "atomadicForge.restartServer" — useful when the user
//   upgrades Forge in their venv and wants to pick up the new server
//   without reloading the whole window.

import * as vscode from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
} from "vscode-languageclient/node";

let client: LanguageClient | undefined;
let outputChannel: vscode.OutputChannel | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  outputChannel = vscode.window.createOutputChannel("Atomadic Forge LSP");
  context.subscriptions.push(outputChannel);

  await startServer(context);

  context.subscriptions.push(
    vscode.commands.registerCommand("atomadicForge.restartServer", async () => {
      await stopServer();
      await startServer(context);
      vscode.window.showInformationMessage("Atomadic Forge LSP restarted.");
    }),
    vscode.commands.registerCommand("atomadicForge.showOutput", () => {
      outputChannel?.show(true);
    }),
    vscode.workspace.onDidChangeConfiguration(async (e) => {
      if (
        e.affectsConfiguration("atomadicForge.serverPath") ||
        e.affectsConfiguration("atomadicForge.serverArgs")
      ) {
        await stopServer();
        await startServer(context);
      }
    }),
  );
}

export async function deactivate(): Promise<void> {
  await stopServer();
}

async function startServer(context: vscode.ExtensionContext): Promise<void> {
  const config = vscode.workspace.getConfiguration("atomadicForge");
  const serverPath = config.get<string>("serverPath", "forge");
  const serverArgs = config.get<string[]>("serverArgs", ["lsp", "serve"]);
  const trace = config.get<string>("trace.server", "off");

  const serverOptions: ServerOptions = {
    command: serverPath,
    args: serverArgs,
    transport: TransportKind.stdio,
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { language: "forge" },
      { scheme: "file", pattern: "**/*.py.forge" },
      { scheme: "file", pattern: "**/*.ts.forge" },
      { scheme: "file", pattern: "**/*.js.forge" },
      { scheme: "file", pattern: "**/*.tsx.forge" },
      { scheme: "file", pattern: "**/*.jsx.forge" },
      { scheme: "file", pattern: "**/*.mjs.forge" },
      { scheme: "file", pattern: "**/*.cjs.forge" },
    ],
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher("**/*.forge"),
    },
    outputChannel,
    traceOutputChannel: outputChannel,
  };

  client = new LanguageClient(
    "atomadicForge",
    "Atomadic Forge LSP",
    serverOptions,
    clientOptions,
  );

  if (trace !== "off") {
    outputChannel?.appendLine(
      `[atomadic-forge] starting server: ${serverPath} ${serverArgs.join(" ")} (trace=${trace})`,
    );
  }

  try {
    await client.start();
    outputChannel?.appendLine("[atomadic-forge] LSP server started.");
  } catch (err) {
    outputChannel?.appendLine(`[atomadic-forge] failed to start: ${err}`);
    vscode.window.showErrorMessage(
      `Atomadic Forge LSP failed to start: ${err}. ` +
        `Check that "${serverPath}" is on your PATH (or set ` +
        `atomadicForge.serverPath in settings).`,
    );
  }
}

async function stopServer(): Promise<void> {
  if (client) {
    try {
      await client.stop();
    } catch (err) {
      outputChannel?.appendLine(`[atomadic-forge] error during stop: ${err}`);
    }
    client = undefined;
  }
}
