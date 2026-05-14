import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from .database import init_db
from .routers import projects, entries, ai, settings, tags, export

app = FastAPI(title="AI 智囊日誌 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/healthz")
def health():
    return {"status": "ok"}


app.include_router(projects.router, prefix="/api")
app.include_router(entries.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    static_dir = os.environ.get("STATIC_DIR", "")
    if not static_dir:
        raise HTTPException(status_code=404, detail="Not found")

    # Serve exact file if it exists (JS, CSS, images, etc.)
    if full_path:
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

    # SPA fallback: return index.html for all other paths
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Frontend not built")
