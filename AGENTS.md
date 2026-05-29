# AI 智囊日誌 (AI-Zhi-Nang-Ri-Zhi)

## 專案目標

Windows 桌面版的 AI 工作日誌 App。Tauri v2 桌面殼包 React 前端 + Python FastAPI sidecar，用 SQLite 存資料，支援 Gemini / OpenAI / 本地 Ollama 三種 AI provider，內建 AI 對話寫日誌、RAG 向量檢索瓶頸分析、目標拆解功能。

## 資料夾結構

- `artifacts/ai-journal/src/` — React 前端（TypeScript + Vite）
  - `pages/` — Journal / Projects / JournalChat / Settings / Dashboard
  - `components/` — 共用 UI、TagSelector 等
  - `components/ui/` — shadcn/ui 元件（**不要手改**）
  - `lib/api.ts` — Tauri-aware fetch wrapper（**所有 API 呼叫必經此**）
  - `lib/mood.ts` — 心情狀態常數
- `artifacts/ai-journal/src-tauri/` — Tauri Rust 殼
  - `sidecars/` — Python binary（**不入 git，每人本地 build**）
- `python_api/` — Python 後端
  - `main.py` — FastAPI app 入口
  - `database.py` — SQLite + migration
  - `ai_client.py` — AI 整合（含 embedding）
  - `routers/` — 各 endpoint
- `lib/api-client-react/` — 生成的 API client（**手動同步 schema**）
- `python-api.spec` — PyInstaller 設定
- `journal.db` — SQLite 資料庫（**含 API key 明文，絕不 commit**）

## 工作流程

當我說「**幫我加一個 [X] 功能**」時：
1. 先讀 `README.md` 或 `AGENTS.md` 確認架構
2. 後端：在 `python_api/routers/` 加 endpoint，必要時加 migration 到 `database.py`
3. 前端：在 `artifacts/ai-journal/src/pages/` 加頁面，用 `apiFetch` 串接
4. 若加新 page → 同時更新 `App.tsx` route + `components/Layout.tsx` 的 nav
5. 後端動到 → 重建 sidecar（見下方）
6. 跑 smoke test 確認 endpoint 通

當我說「**改後端 [X]**」時：
1. 修 `python_api/` 對應檔案
2. 必須跑 `pnpm api:build` 重建 sidecar（不然 Tauri 還在用舊 binary）
3. 重啟 `tauri:dev`

當我說「**改前端 [X]**」時：
1. 直接改 `artifacts/ai-journal/src/`
2. Vite HMR 自動套用，**不用重啟**

當我說「**上 git**」或「**push**」時：
1. `git status` 確認沒有意外的檔案
2. **絕對不能 commit `journal.db`、`build/`、`dist/`、`target/`、sidecar `.exe`**
3. Commit message 用繁體中文，分段條列改動
4. 若 remote 有新 commit，先 `git pull --rebase` 再 push

當我說「**重建 sidecar**」時：
1. `Get-Process python-api | Stop-Process -Force`（殺掉舊 process 避免 PermissionDenied）
2. `pnpm api:build`（會 build 前端 + PyInstaller + 自動複製到 sidecars）
3. 重啟 `tauri:dev`

## 工具偏好

### 前端
- **語言**：TypeScript（嚴格 mode）
- **UI 元件**：shadcn/ui + Tailwind CSS（**不要引入新 UI library**）
- **狀態管理**：TanStack Query（server state）+ useState（local state）
- **路由**：wouter + hash routing（Tauri 環境用）
- **圖示**：lucide-react
- **日期**：date-fns（不要用 moment）
- **API 呼叫**：一律用 `@/lib/api` 的 `apiFetch`，**禁止用 raw `fetch()`**

### 後端
- **框架**：FastAPI + Pydantic v2
- **資料庫**：SQLite（用內建 `sqlite3`，不要引 ORM）
- **AI**：`requests` 直接呼叫 Gemini REST API、`openai` SDK 給 OpenAI 與本地 Ollama
- **檔案對話框**：`tkinter`（避免引入 Tauri 檔案系統 plugin）
- **PyInstaller**：lazy import 必須寫進 `python-api.spec` 的 `hiddenimports`

### 寫程式風格
- **錯誤處理**：寫使用者面向的繁體中文錯誤訊息，技術細節放在 log
- **註解**：複雜邏輯用中文寫意圖，不寫廢話註解（不要 `# 設定變數`）
- **命名**：python `snake_case`，TypeScript `camelCase`，元件 `PascalCase`
- **檔案大小**：單一前端頁面超過 600 行考慮拆分

## 限制

> **絕對不能 commit `journal.db`** — 裡面有 AI API key 明文。`.gitignore` 已包含但每次 commit 前都要 `git status` 確認沒被加進來

> **前端禁止使用 raw `fetch()`** — Tauri WebView origin 是 `https://tauri.localhost/`，`fetch('/api/...')` 會發到錯的 host。一律用 `apiFetch` from `@/lib/api`

> **錯誤訊息不可洩漏 API key** — 給 LLM 的 URL 或 error string 必須先用 `replace(api_key, "***KEY***")` 遮蔽

> **改 Python 後一定要重建 sidecar** — Tauri 啟動時複製 sidecar binary 到自己的快取，光改 `.py` 不會生效

> **Python lazy import 必須寫進 `python-api.spec`** — 例：`from openai import OpenAI` 在 function 內部，PyInstaller 偵測不到，會在 bundled binary 報 `ImportError`

> **不要自動執行 `git commit` / `git push`** — 必須我明確說「commit」或「push」才執行；只有 `git status` / `git diff` / `git log` 可以隨時跑

> **不要 `git rebase -i` 或 `git push --force`** — 除非我明確指示，這些會改寫歷史影響協作者

> **不要引入新的大型套件** — 例如 ChromaDB、Drizzle ORM、redux 等；現有架構刻意保持輕量

> **不要建立 `*.md` 文件除非我要求** — 包含 README、設計文件、變更日誌；專案已有 README 與 AGENTS.md

> **桌面 binary 是 per-machine 的** — `artifacts/ai-journal/src-tauri/sidecars/*.exe` 不入 git，每人 clone 後要 `pnpm setup` 自己 build

## 常用指令速查

```powershell
pnpm tauri:dev           # 啟動開發環境
pnpm api:build           # 重建 Python sidecar（含複製）
pnpm setup               # 一鍵安裝（前端 + Python + sidecar）
pnpm tauri:build         # 打包 .msi / .exe 安裝檔
git log --oneline -10    # 看最近 commit
```

## AI Provider 預設值

- **預設 provider**：Gemini（`gemini-2.5-flash` 自動 fallback 到舊版）
- **OpenAI**：`gpt-4o-mini`
- **本地**：建議 `qwen2.5:7b`（中文最佳），embedding 用 `nomic-embed-text`
- **不要用 270M 等迷你模型**，無法穩定輸出 JSON
