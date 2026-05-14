# AI 智囊日誌 (AI-Zhi-Nang-Ri-Zhi)

一個 Windows 桌面版的 AI 工作日誌應用，支援多種 AI 模型（Google Gemini、OpenAI ChatGPT、本地 Ollama）做日誌分析與目標拆解。

---

## 🏗️ 技術架構

```
┌──────────────────────────────────────────────────┐
│  Tauri v2 (Rust)  ── 桌面殼，管理視窗 & sidecar  │
│  ┌────────────────────────────────────────────┐  │
│  │ React + Vite + TypeScript (前端 WebView)   │  │
│  │   - shadcn/ui + Tailwind                   │  │
│  │   - TanStack Query, wouter (hash routing)  │  │
│  └────────────────┬───────────────────────────┘  │
│                   │ apiFetch → 127.0.0.1:8080    │
│  ┌────────────────▼───────────────────────────┐  │
│  │ Python FastAPI sidecar (PyInstaller bundle)│  │
│  │   - SQLite (journal.db)                    │  │
│  │   - AI integration (Gemini/OpenAI/Local)   │  │
│  │   - tkinter 原生檔案對話框 (Markdown 匯出) │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

---

## 🧰 環境需求

| 工具 | 用途 | 安裝 |
|------|------|------|
| **Git** | 版本控制 | [git-scm.com](https://git-scm.com) |
| **Node.js 20+** | 前端開發 | [nodejs.org](https://nodejs.org) LTS |
| **pnpm** | 套件管理 | `npm install -g pnpm` |
| **Python 3.10–3.13** | 後端開發 + PyInstaller 打包 | [python.org](https://www.python.org/downloads/)（勾 **Add to PATH**） |
| **Rust + Cargo** | 編譯 Tauri | [rustup.rs](https://rustup.rs) |
| **VS Build Tools 2022** | Rust 在 Windows 需要 C++ 編譯器 | [VS Build Tools](https://visualstudio.microsoft.com/downloads/?q=build+tools)，勾「**使用 C++ 的桌面開發**」 |
| **WebView2 Runtime** | Tauri 渲染（Win11 內建，Win10 需手動裝） | [WebView2](https://developer.microsoft.com/microsoft-edge/webview2) |

### 可選

- **Ollama**（[ollama.com](https://ollama.com)）— 想用本地 AI 模型
- **DB Browser for SQLite** — 直接看 `journal.db` 內容
- **VS Code** + Rust-analyzer / Python / Tailwind CSS 擴充套件

---

## 🚀 第一次設定

```powershell
# 1. clone
git clone <your-repo-url>
cd AI-Zhi-Nang-Ri-Zhi

# 2. 前端套件（會幫所有 workspace 安裝）
pnpm install

# 3. Python 套件
pip install -r python_api\requirements.txt

# 4. 第一次跑 tauri:dev 時 Windows 會彈防火牆，按「允許」
```

---

## 💻 日常開發

### 啟動開發環境

```powershell
pnpm tauri:dev
```

這會同時啟動：
- Vite dev server（前端，自動 HMR）
- Python sidecar（後端 API 在 `127.0.0.1:8080`）
- Tauri 桌面視窗

### 改前端

直接改 `artifacts/ai-journal/src/` 下的檔案，Vite HMR 會自動套用，**不用重啟**。

### 改後端 Python

每次改完 Python 都要重建 sidecar，否則 Tauri 還在用舊版 binary：

```powershell
# 1. 殺掉舊 process（不殺會 PermissionDenied）
Get-Process python-api -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. 重建 binary
python -m PyInstaller python-api.spec --noconfirm

# 3. 複製到 Tauri sidecars 目錄
copy dist\python-api.exe artifacts\ai-journal\src-tauri\sidecars\python-api-x86_64-pc-windows-msvc.exe

# 4. 重啟 tauri:dev
```

**一行串起來**：
```powershell
Get-Process python-api -ErrorAction SilentlyContinue | Stop-Process -Force; python -m PyInstaller python-api.spec --noconfirm; copy dist\python-api.exe artifacts\ai-journal\src-tauri\sidecars\python-api-x86_64-pc-windows-msvc.exe
```

### 後端單獨測試（不透過 Tauri）

```powershell
cd python_api
python run_api.py
# 開 http://127.0.0.1:8080/docs 看 Swagger UI
```

---

## 📦 打包安裝檔

```powershell
# 1. 先確認 sidecar 是最新版（見上面「改後端」流程）
# 2. 打包
pnpm tauri:build
```

產出位置：`artifacts\ai-journal\src-tauri\target\release\bundle\`
- `msi\` — MSI 安裝檔
- `nsis\` — NSIS 安裝檔（.exe）

---

## ⚠️ 重要規則

### 1. 前端絕對不要用 raw `fetch()`

Tauri WebView 的 origin 是 `https://tauri.localhost/`，`fetch('/api/...')` 會發到錯的 host。一定要用 `apiFetch`：

```typescript
import { apiFetch } from "@/lib/api";

// ✅ 正確
const data = await apiFetch<MyType>("/api/journals");

// ❌ 錯誤（在 Tauri 環境會 fail）
const res = await fetch("/api/journals");
```

`apiFetch` 會自動偵測是否在 Tauri 並補上 `http://127.0.0.1:8080`。

### 2. 新加 Python lazy import 要寫進 spec

如果在 function 內部 `import xxx`（lazy import），PyInstaller 自動偵測不到，要手動加進 `python-api.spec` 的 `hiddenimports`：

```python
hiddenimports=[
    "tkinter", "tkinter.filedialog",
    "openai", "openai.resources",
    "你的新套件",  # ← 加在這
],
```

### 3. 不要 commit `journal.db`

`journal.db` 含 AI API key（明文）。已加進 `.gitignore`，但**每人有自己的本地資料庫**，不應該共用。

---

## 📁 專案結構

```
AI-Zhi-Nang-Ri-Zhi/
├── artifacts/ai-journal/          # React/Vite 前端 (Tauri WebView)
│   ├── src/
│   │   ├── pages/                 # Journal / Projects / Settings
│   │   ├── components/            # 共用 UI、TagSelector 等
│   │   ├── components/ui/         # shadcn/ui 元件
│   │   └── lib/api.ts             # ⚠️ Tauri-aware fetch wrapper
│   └── src-tauri/                 # Tauri Rust 設定
│       ├── Cargo.toml
│       ├── tauri.conf.json
│       └── sidecars/              # Python binary 放這（不入 git）
├── python_api/                    # Python FastAPI 後端
│   ├── main.py                    # App entry + router 註冊
│   ├── run_api.py                 # uvicorn 啟動腳本
│   ├── database.py                # SQLite 連線
│   ├── ai_client.py               # AI 整合（Gemini/OpenAI/Local）
│   ├── routers/
│   │   ├── settings.py            # AI 金鑰、模板、分類 CRUD
│   │   ├── journals.py            # 日誌
│   │   ├── projects.py            # 專案
│   │   ├── tags.py                # 標籤
│   │   └── export.py              # Markdown 匯出（tkinter 對話框）
│   └── requirements.txt
├── python-api.spec                # PyInstaller spec
├── package.json                   # 根 workspace
├── pnpm-workspace.yaml
└── README.md
```

---

## 🗄️ 資料庫

`journal.db`（SQLite，自動建立）的主要 table：

| Table | 用途 |
|-------|------|
| `entries` | 日誌記錄 |
| `projects` | 專案 |
| `tags` / `entry_tags` | 標籤系統 |
| `settings` | 通用 key-value：AI provider、API keys、模板、分類等 |

完全重置：
```powershell
Remove-Item journal.db
# 下次啟動會自動建立空白資料庫
```

---

## 🤖 AI 設定

App 內建三種 AI provider，在「設定」頁切換：

| Provider | 模型 | 設定 |
|----------|------|------|
| **Google Gemini** | 預設 `gemini-2.5-flash`（會自動 fallback） | 申請 [AI Studio key](https://aistudio.google.com/app/apikey) |
| **OpenAI ChatGPT** | `gpt-4o-mini` | 申請 [Platform key](https://platform.openai.com/api-keys)（需儲值 $5+） |
| **本地模型 (Ollama / LM Studio)** | 任意 OpenAI 相容服務 | 填 Base URL + 模型名稱 |

本地模型建議用 **`qwen2.5:7b`**（中文最佳）或 **`gemma2:2b`**（小巧快速）。
270M 等級的迷你模型無法穩定輸出 JSON，會分析失敗。

---

## 🐛 常見問題

| 問題 | 解法 |
|------|------|
| `pyinstaller: command not found` | 用 `python -m PyInstaller` |
| 改了 Python 沒效果 | 忘記重建 sidecar；見「改後端 Python」流程 |
| `PermissionDenied` on `.exe` | 舊 python-api process 還在跑，先 `Stop-Process` |
| Port 8080 被佔用 | `Get-NetTCPConnection -LocalPort 8080` 查誰，殺掉 |
| AI 分析 JSON parse 失敗 | 本地模型太小，換 7B 以上 |
| Tauri 建置 Rust 錯誤 | VS Build Tools 沒裝、或缺 C++ 桌面開發工作負載 |
"" 
_最後更新：$(Get-Date -Format 'yyyy-MM-dd')_
