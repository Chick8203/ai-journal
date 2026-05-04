import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import projects, entries, ai

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
