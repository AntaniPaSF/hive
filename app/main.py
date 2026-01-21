from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.citations import enforce_citations, CitationError

app = FastAPI(title="Corporate Digital Assistant (Local MVP)")

# Serve minimal static UI
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    with open("app/ui/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.post("/ask")
def ask(payload: dict):
    try:
        citations = enforce_citations(payload)
        # MVP: echo back with citation enforcement; real retrieval to be added in future stories
        return JSONResponse({
            "message": "Answer would be generated here.",
            "citations": citations,
            "note": "This MVP enforces citations; content generation is out-of-scope for skeleton."
        })
    except CitationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/demo")
def demo():
    # Provide a canned demo response with a citation referencing sample policy doc
    return JSONResponse({
        "message": "Vacation policy allows 20 days per year (example).",
        "citations": [{
            "doc": "sample-policies.md",
            "section": "Vacation Policy §1"
        }]
    })
