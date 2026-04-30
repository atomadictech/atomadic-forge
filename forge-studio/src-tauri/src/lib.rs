use std::io::{BufRead, BufReader, BufWriter, Write};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};

use serde_json::Value;
use tauri::State;

struct ForgeSession {
    child: Child,
    stdin: BufWriter<std::process::ChildStdin>,
    stdout: BufReader<std::process::ChildStdout>,
    next_id: u32,
}

impl ForgeSession {
    fn spawn(project_root: &str) -> Result<Self, String> {
        let mut child = Command::new("forge")
            .args(["mcp", "serve", "--project-root", project_root])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| {
                if e.kind() == std::io::ErrorKind::NotFound {
                    "forge not found on PATH — install with: pip install atomadic-forge".to_string()
                } else {
                    format!("failed to start forge: {e}")
                }
            })?;
        let stdin = child.stdin.take().ok_or("child has no stdin")?;
        let stdout = child.stdout.take().ok_or("child has no stdout")?;
        Ok(Self { child, stdin: BufWriter::new(stdin), stdout: BufReader::new(stdout), next_id: 1 })
    }

    fn rpc_call(&mut self, method: &str, params: Value) -> Result<Value, String> {
        let id = self.next_id;
        self.next_id += 1;
        let req = serde_json::json!({ "jsonrpc": "2.0", "id": id, "method": method, "params": params });
        let line = serde_json::to_string(&req).map_err(|e| e.to_string())? + "\n";
        self.stdin.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
        self.stdin.flush().map_err(|e| e.to_string())?;
        loop {
            let mut buf = String::new();
            let n = self.stdout.read_line(&mut buf).map_err(|e| e.to_string())?;
            if n == 0 { return Err("forge process closed stdout unexpectedly".to_string()); }
            let trimmed = buf.trim();
            if trimmed.is_empty() { continue; }
            let resp: Value = serde_json::from_str(trimmed).map_err(|e| format!("bad JSON: {e}"))?;
            if resp.get("id").and_then(|v| v.as_u64()) == Some(id as u64) { return Ok(resp); }
        }
    }

    fn notify(&mut self, method: &str) -> Result<(), String> {
        let msg = serde_json::json!({ "jsonrpc": "2.0", "method": method, "params": {} });
        let line = serde_json::to_string(&msg).map_err(|e| e.to_string())? + "\n";
        self.stdin.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
        self.stdin.flush().map_err(|e| e.to_string())
    }
}

pub struct AppState {
    session: Arc<Mutex<Option<ForgeSession>>>,
}

#[tauri::command]
fn forge_connect(project_root: String, state: State<'_, AppState>) -> Result<String, String> {
    let mut guard = state.session.lock().map_err(|e| e.to_string())?;
    if let Some(mut old) = guard.take() { let _ = old.child.kill(); }
    let mut session = ForgeSession::spawn(&project_root)?;
    let _init = session.rpc_call("initialize", serde_json::json!({
        "protocolVersion": "2024-11-05",
        "capabilities": { "roots": { "listChanged": false } },
        "clientInfo": { "name": "forge-studio", "version": "0.1.0" },
    }))?;
    session.notify("notifications/initialized")?;
    *guard = Some(session);
    Ok("connected".to_string())
}

#[tauri::command]
fn forge_disconnect(state: State<'_, AppState>) -> Result<(), String> {
    let mut guard = state.session.lock().map_err(|e| e.to_string())?;
    if let Some(mut s) = guard.take() { let _ = s.child.kill(); }
    Ok(())
}

#[tauri::command]
fn forge_tools_list(state: State<'_, AppState>) -> Result<Value, String> {
    with_session(&state, |s| extract_result(s.rpc_call("tools/list", serde_json::json!({}))?))
}

#[tauri::command]
fn forge_resources_list(state: State<'_, AppState>) -> Result<Value, String> {
    with_session(&state, |s| extract_result(s.rpc_call("resources/list", serde_json::json!({}))?))
}

#[tauri::command]
fn forge_call_tool(name: String, arguments: Value, state: State<'_, AppState>) -> Result<Value, String> {
    with_session(&state, |s| {
        let resp = s.rpc_call("tools/call", serde_json::json!({ "name": name, "arguments": arguments }))?;
        extract_result(resp)
    })
}

fn with_session<F, T>(state: &State<'_, AppState>, f: F) -> Result<T, String>
where F: FnOnce(&mut ForgeSession) -> Result<T, String> {
    let mut guard = state.session.lock().map_err(|e| e.to_string())?;
    let session = guard.as_mut().ok_or("not connected — call forge_connect first")?;
    f(session)
}

fn extract_result(resp: Value) -> Result<Value, String> {
    if let Some(err) = resp.get("error") { return Err(err.to_string()); }
    if let Some(text) = resp.get("result").and_then(|r| r.get("content"))
        .and_then(|c| c.as_array()).and_then(|a| a.first())
        .and_then(|item| item.get("text")).and_then(|t| t.as_str()) {
        if let Ok(parsed) = serde_json::from_str::<Value>(text) { return Ok(parsed); }
        return Ok(Value::String(text.to_string()));
    }
    resp.get("result").cloned().ok_or_else(|| format!("unexpected response shape: {resp}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState { session: Arc::new(Mutex::new(None)) })
        .invoke_handler(tauri::generate_handler![
            forge_connect, forge_disconnect, forge_tools_list, forge_resources_list, forge_call_tool,
        ])
        .run(tauri::generate_context!())
        .expect("error while running forge-studio");
}
