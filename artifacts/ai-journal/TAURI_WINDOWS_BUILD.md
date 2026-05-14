# AI 智囊日誌：Tauri Windows 打包指南

本專案已加入 Tauri 桌面殼，並設定為：
- 前端：`artifacts/ai-journal`
- 桌面殼：`artifacts/ai-journal/src-tauri`
- API：`python_api`（使用 SQLite）
- SQLite 位置：`%LOCALAPPDATA%/com.aijournal.desktop/journal.db`

## 1) 安裝必要工具（Windows）

1. 安裝 Rust（含 Cargo）
   - https://www.rust-lang.org/tools/install
2. 安裝 Visual Studio C++ Build Tools
   - 勾選「Desktop development with C++」
3. 安裝 WebView2 Runtime（通常 Win11 已內建）
4. 安裝 Python 3.11+（建議勾選 Add to PATH）
5. 安裝 Node.js 20+（含 Corepack）

## 2) 安裝 JavaScript 依賴

在 repo 根目錄執行：

```powershell
corepack enable
corepack pnpm install
```

> 如果你在 PowerShell 看到 `sh` 找不到，請改用 Git Bash 執行上面指令。

## 3) 建立 Python API sidecar（`python-api.exe`）

在 repo 根目錄執行：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r python_api\requirements.txt pyinstaller
pyinstaller --onefile --name python-api python_api\run_api.py
```

產物在：`dist/python-api.exe`

把檔案複製到：

`artifacts/ai-journal/src-tauri/sidecars/python-api-x86_64-pc-windows-msvc.exe`

> `externalBin` 會使用 target triple 命名，所以檔名需帶 `-x86_64-pc-windows-msvc`。

## 4) 開發模式（桌面 App）

在 repo 根目錄執行：

```powershell
corepack pnpm --filter @workspace/ai-journal run tauri:dev
```

## 5) 打包 `.exe`

在 repo 根目錄執行：

```powershell
corepack pnpm --filter @workspace/ai-journal run tauri:build
```

輸出檔案在：

`artifacts/ai-journal/src-tauri/target/release/bundle/nsis/`

裡面會有安裝程式 `.exe`。

## 6) 本地 SQLite 驗證

第一次啟動後，確認檔案存在：

`%LOCALAPPDATA%/com.aijournal.desktop/journal.db`

這代表桌面版已經使用本機 SQLite，而不是雲端資料庫。
