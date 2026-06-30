import os
import json
import time
import requests
from tools import search_web, fetch_page

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # fast, free-tier friendly

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={{key}}"

SYSTEM_PROMPT = """You are a research assistant agent. You have two tools:

1. search_web(query) - search the web for information
2. fetch_page(url) - fetch and read the content of a specific URL

Respond ONLY in JSON, with no preamble or markdown formatting, in one of these forms:

To call a tool:
{"action": "search_web", "query": "..."}
{"action": "fetch_page", "url": "..."}

To finish:
{"action": "finish", "answer": "Your synthesized answer here. You MUST include the literal https:// URLs of every source you cite, inline in the text, not just the source name."}

Rules:
- Do not search more than 3 times.
- After gathering enough information, you MUST call finish with your answer.
- Your final answer MUST include literal https:// URLs for every claim, not just source names like "according to Wikipedia". Paste the actual URL.
- Base your answer only on information you actually retrieved via tools.
"""


def call_groq(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_gemini(messages):
    # Gemini uses a different message format: no "system" role, and content is "parts".
    system_text = ""
    contents = []
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n"
        else:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

    if system_text and contents:
        contents[0]["parts"][0]["text"] = system_text + "\n" + contents[0]["parts"][0]["text"]

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }
    url = GEMINI_URL.format(key=GEMINI_API_KEY)
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def call_llm(messages):
    """Try Groq first (fast, primary). Fall back to Gemini on any error
    (rate limit, timeout, outage) if a Gemini key is configured."""
    try:
        return call_groq(messages)
    except Exception as groq_error:
        if not GEMINI_API_KEY:
            raise groq_error
        try:
            return call_gemini(messages)
        except Exception as gemini_error:
            raise RuntimeError(
                f"Both providers failed. Groq: {groq_error} | Gemini: {gemini_error}"
            )


def run_agent(question, max_iterations=6, verbose=True):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    transcript = []
    seen_urls = set()
    answer = None

    for i in range(max_iterations):
        if i == max_iterations - 2:
            messages.append({
                "role": "user",
                "content": "You are running out of iterations. Based on everything gathered so far, respond now with the finish action and your best synthesized answer, including literal https:// URLs for your sources."
            })

        try:
            raw = call_llm(messages)
        except Exception as e:
            print(f"[agent error] iter {i}: {e}", flush=True)
            transcript.append({"iter": i, "error": str(e)})
            break

        messages.append({"role": "assistant", "content": raw})

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            messages.append({"role": "user", "content": "Invalid JSON. Respond ONLY with valid JSON in the specified format."})
            continue

        action = parsed.get("action")

        if action == "finish":
            answer = parsed.get("answer", "")
            transcript.append({"iter": i, "action": "finish"})
            break

        elif action == "search_web":
            query = parsed.get("query", "")
            if verbose:
                print(f"[iter {i}] search_web: {query}")
            try:
                results = search_web(query)
            except Exception as e:
                results = f"ERROR: {e}"
            transcript.append({"iter": i, "action": "search_web", "query": query})
            messages.append({"role": "user", "content": f"Search results:\n{results}"})

        elif action == "fetch_page":
            url = parsed.get("url", "")
            if verbose:
                print(f"[iter {i}] fetch_page: {url}")
            seen_urls.add(url)
            try:
                result = fetch_page(url)
            except Exception as e:
                result = f"ERROR: {e}"
            transcript.append({"iter": i, "action": "fetch_page", "url": url})
            messages.append({"role": "user", "content": f"Page content:\n{result}"})

        else:
            messages.append({"role": "user", "content": "Unknown action. Use search_web, fetch_page, or finish."})

    os.makedirs("sessions", exist_ok=True)
    session_id = f"session_{int(time.time())}"
    session = {
        "id": session_id,
        "question": question,
        "answer": answer,
        "finished": answer is not None,
        "iterations_used": len(transcript),
        "max_iterations_allowed": max_iterations,
        "transcript": transcript,
        "fetched_urls": list(seen_urls),
    }
    with open(f"sessions/{session_id}.json", "w") as f:
        json.dump(session, f, indent=2)

    if verbose:
        print(f"(session saved to sessions/{session_id}.json)")
        print("=== FINAL ANSWER ===")
        print(answer if answer else "Max iterations reached without final answer.")

    return session


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What are the latest developments in fusion energy?"
    run_agent(q)