import os
import sys

import uvicorn


def _resolve_static_dir() -> str:
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle — static files are bundled at sys._MEIPASS/public
        return os.path.join(sys._MEIPASS, "public")  # type: ignore[attr-defined]
    # Running in development — find project root (this file is at python_api/run_api.py)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "artifacts", "ai-journal", "dist", "public")


def main() -> None:
    static_dir = _resolve_static_dir()
    if os.path.isdir(static_dir):
        os.environ["STATIC_DIR"] = static_dir

    # Import the app object directly so PyInstaller can trace all dependencies at
    # build time. Using the string form "python_api.main:app" causes
    # ModuleNotFoundError inside a frozen bundle.
    from python_api.main import app

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
