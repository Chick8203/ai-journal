# AI 智囊日誌

A personal AI-powered work journal application with Gemini AI integration.

## Architecture

### Frontend (React + Vite)
- **Path**: `artifacts/ai-journal/`
- **Preview**: `/` (root)
- **Port**: 25418
- **Framework**: React + Vite + TailwindCSS + shadcn/ui
- **State**: TanStack Query with generated API hooks from `@workspace/api-client-react`
- **Routing**: wouter

### Backend (Python FastAPI)
- **Path**: `python_api/` (workspace root)
- **Preview**: `/api`
- **Port**: 8080
- **Start script**: `artifacts/api-server/start_api.sh`
- **Database**: SQLite at `journal.db` (workspace root)
- **AI**: Google Gemini via Replit AI Integrations (no API key needed)

### API Spec
- **Path**: `lib/api-spec/openapi.yaml`
- **Codegen**: `pnpm --filter @workspace/api-spec run codegen` → generates React Query hooks to `lib/api-client-react/src/generated/`

## Database Schema (SQLite)

```sql
CREATE TABLE projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  category TEXT NOT NULL DEFAULT 'general',  -- engineering|office|general
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  content TEXT NOT NULL,
  project_id INTEGER NOT NULL REFERENCES projects(id),
  template TEXT NOT NULL DEFAULT 'freeform',  -- engineering|office|freeform
  mood INTEGER,  -- 1-5 scale
  tags TEXT NOT NULL DEFAULT '[]',  -- JSON array
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## Features

- **日誌記錄**: Create/edit/delete journal entries with date, content, project, template, mood, and tags
- **專案管理**: Organize entries by project with engineering/office/general categories
- **模板系統**: Engineering template (今日目標/完成事項/瓶頸/明日計畫) and Office template (今日重點/心得筆記/行動項目)
- **AI 分析瓶頸**: Gemini analyzes work efficiency using first/second derivative logic
- **AI 目標拆解**: Gemini breaks down big goals into step-by-step SOP
- **統計面板**: Dashboard with streak, entry counts, recent activity

## Python API Structure

```
python_api/
├── __init__.py
├── main.py          # FastAPI app + CORS + startup
├── database.py      # SQLite connection + init_db()
├── gemini_client.py # Gemini AI client via Replit integration
└── routers/
    ├── __init__.py
    ├── projects.py  # CRUD for projects
    ├── entries.py   # CRUD for entries + stats summary
    └── ai.py        # analyze-bottleneck + decompose-goal
```

## Environment Variables

- `AI_INTEGRATIONS_GEMINI_BASE_URL` — Auto-set by Replit Gemini integration
- `AI_INTEGRATIONS_GEMINI_API_KEY` — Auto-set by Replit Gemini integration
- `SESSION_SECRET` — Session secret
- `DB_PATH` — SQLite database path (default: `journal.db`)

## Workflows

- **AI 智囊日誌** (`artifacts/ai-journal: web`): React frontend dev server
- **API Server** (`artifacts/api-server: API Server`): Python FastAPI via `start_api.sh`

## Running Locally

Backend starts automatically via the "API Server" workflow using:
```bash
bash /home/runner/workspace/artifacts/api-server/start_api.sh
```

Which runs:
```bash
cd /home/runner/workspace
uvicorn python_api.main:app --host 0.0.0.0 --port 8080 --reload
```
