import tkinter as tk
from tkinter import filedialog
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/export", tags=["export"])


class ExportMarkdownBody(BaseModel):
    content: str
    filename: str


@router.post("/markdown")
def export_markdown(body: ExportMarkdownBody):
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    filepath = filedialog.asksaveasfilename(
        defaultextension=".md",
        filetypes=[("Markdown 檔案", "*.md"), ("所有檔案", "*.*")],
        initialfile=body.filename,
        title="儲存 Markdown 匯出",
    )
    root.destroy()
    if not filepath:
        return {"saved": False, "path": ""}
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(body.content)
    return {"saved": True, "path": filepath}
