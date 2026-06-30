from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from agent import run_agent

app = FastAPI(title="Research Agent")


class AskRequest(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def root():
    with open("static/index.html") as f:
        return f.read()


@app.post("/ask")
def ask(req: AskRequest):
    session = run_agent(req.question, max_iterations=6, verbose=False)
    error_detail = None
    for step in session["transcript"]:
        if "error" in step:
            error_detail = step["error"]
    return {
        "answer": session["answer"] or "Sorry, I couldn't find a complete answer in time.",
        "finished": session["finished"],
        "iterations_used": session["iterations_used"],
        "error_detail": error_detail,
    }