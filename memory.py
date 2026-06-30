"""
Memory/state for the research agent.

A "session" holds everything about one research task: the question, the
full message transcript (including tool calls and results), every URL
actually seen during the run (used to validate citations), and the final
answer. Sessions are persisted to disk as JSON so a long-running or
interrupted task can be inspected, resumed, or audited later -- this is
the agent's external memory, separate from the model's own context.
"""

import json
import os
import uuid
from datetime import datetime, timezone

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")


class Session:
    def __init__(self, question: str, max_iterations: int = 6):
        self.id = str(uuid.uuid4())[:8]
        self.question = question
        self.max_iterations = max_iterations
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.messages = []          # full Claude message transcript
        self.seen_urls = set()      # every URL surfaced by a tool, for citation validation
        self.iterations = 0
        self.final_answer = None
        self.final_sources = None
        self.status = "running"     # running | finished | max_iterations_hit | error

    def record_urls(self, urls):
        self.seen_urls.update(urls)

    def to_dict(self):
        d = {
            "id": self.id,
            "question": self.question,
            "created_at": self.created_at,
            "max_iterations": self.max_iterations,
            "iterations": self.iterations,
            "status": self.status,
            "seen_urls": sorted(self.seen_urls),
            "final_answer": self.final_answer,
            "final_sources": self.final_sources,
            "messages": self.messages,
        }
        return d

    def save(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        path = os.path.join(SESSIONS_DIR, f"{self.id}.json")
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        return path

    @classmethod
    def load(cls, session_id: str):
        path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        with open(path) as f:
            data = json.load(f)
        s = cls(data["question"], data["max_iterations"])
        s.id = data["id"]
        s.created_at = data["created_at"]
        s.iterations = data["iterations"]
        s.status = data["status"]
        s.seen_urls = set(data["seen_urls"])
        s.final_answer = data["final_answer"]
        s.final_sources = data["final_sources"]
        s.messages = data["messages"]
        return s