"""
Entry point that puts both the project root (for `ml.*` imports) and this
`backend/` directory (for `app.*` imports) on sys.path, then launches uvicorn.
Run from anywhere: python backend/run.py
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, app_dir=str(BACKEND_DIR))
