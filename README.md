# Research Agent

A research assistant agent that searches the web, fetches pages, and synthesizes a cited answer to your question. Built as a small agentic loop on top of an LLM, wrapped in a FastAPI backend with a minimal web frontend.

## How it works

The agent runs a tool-use loop:

1. The LLM is given a question and two tools: `search_web(query)` and `fetch_page(url)`.
2. On each turn, the model responds in JSON choosing to either call a tool or finish with a synthesized answer.
3. The loop runs for up to 6 iterations, after which the agent is nudged to wrap up with whatever it has gathered.
4. The final answer must include literal source URLs, not just source names, so claims are traceable.
5. Every run is logged to a JSON file in `sessions/` for inspection.

## Architecture

```
research-agent/
├── agent.py          # core agent loop + LLM call logic
├── tools.py          # search_web and fetch_page implementations
├── main.py           # FastAPI app: serves frontend + /ask endpoint
├── static/index.html # minimal single-page frontend
├── eval/              # eval harness with test cases and pass/fail checks
├── requirements.txt
└── render.yaml        # Render deployment config
```

## LLM backend

The agent currently runs on **Groq** (`llama-3.1-8b-instant`), using Groq's free, no-credit-card API tier. The code also supports a fallback to **Google Gemini** if a `GEMINI_API_KEY` is set, so the app keeps working if Groq's rate limit is hit — but this is optional and currently unused.

Earlier development iterations of this project ran entirely locally using **Ollama** with `llama3.1`. That version required no API key or internet-dependent LLM calls, useful for offline development, but couldn't be deployed for public use without users running Ollama themselves. The current Groq-based version replaces that for the deployed app.

## Running locally

```bash
pip install -r requirements.txt
```

Set your Groq API key (get one free at console.groq.com):

```powershell
# PowerShell
$env:GROQ_API_KEY="your_key_here"
```

```bash
# macOS/Linux
export GROQ_API_KEY="your_key_here"
```

Run the server:

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000` and ask a question.

You can also run the agent directly from the command line without the web UI:

```bash
python agent.py "What are the latest developments in fusion energy?"
```

## Evaluation

The `eval/` folder contains a small harness that runs the agent against a fixed set of test questions and checks:

- whether the agent finished within its iteration budget
- whether it stayed within budget
- whether it cited real URLs it actually fetched (no hallucinated sources)
- whether it included enough citations to support its answer

Run it with:

```bash
python eval/run_eval.py
```

Results are saved to `eval/eval_report.json`.

## Deployment

This app is deployed on [Render](https://render.com) using the included `render.yaml`:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment variable required: `GROQ_API_KEY`

On the free tier, the service spins down after inactivity, so the first request after idle time may take 30-60 seconds.

## Known limitations

- `llama-3.1-8b-instant` is a small model, so tool-use JSON output is occasionally malformed (the agent retries on invalid JSON, but this adds latency).
- `fetch_page` uses a lightweight regex-based HTML strip rather than a full parser, so page text extraction is imperfect on complex layouts.
- Groq's free tier has rate limits (30 requests/min, daily caps), so heavy concurrent traffic may trigger errors. A Gemini fallback is implemented but not currently enabled.

## Future improvements

- Enable the Gemini fallback for resilience under load
- Swap the HTML stripping in `tools.py` for a proper parser (e.g. BeautifulSoup)
- Add retry/backoff handling for rate-limit errors
- Persist session history in a database instead of flat JSON files