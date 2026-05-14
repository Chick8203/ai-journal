#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{AppHandle, Manager};
// 關鍵：必須引入 ShellExt 才能使用 .shell() 擴充方法
use tauri_plugin_shell::ShellExt;

fn spawn_python_api(app: &AppHandle) -> Result<(), String> {
    let app_data_dir = app
        .path()
        .app_local_data_dir()
        .map_err(|e| format!("failed to resolve app data directory: {e}"))?;

    std::fs::create_dir_all(&app_data_dir)
        .map_err(|e| format!("failed to create app data directory: {e}"))?;

    let db_path = app_data_dir.join("journal.db");
    let db_path_str = db_path.to_string_lossy().to_string();

    // 修改處：在 v2 中，要從 app 實體獲取 shell 插件，再建立 sidecar
    let sidecar = app
        .shell()
        .sidecar("python-api")
        .map_err(|e| format!("failed to locate sidecar binary: {e}"))?
        .env("DB_PATH", db_path_str)
        .env("PORT", "8080");

    let (_receiver, _child) = sidecar
        .spawn()
        .map_err(|e| format!("failed to spawn python api sidecar: {e}"))?;

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // 這裡傳入 app.handle() 是正確的
            if let Err(err) = spawn_python_api(app.handle()) {
                eprintln!("{err}");
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}