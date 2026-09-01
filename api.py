from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "MiniApp backend is running!"}
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def serve_html():
    html_path = Path(__file__).parent / "index.html"
    return html_path.read_text(encoding="utf-8")
