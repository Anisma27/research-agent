import requests
from ddgs import DDGS


def search_web(query, max_results=5):
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
        lines = []
        for r in results:
            title = r.get("title", "")
            url = r.get("href", r.get("url", ""))
            body = r.get("body", "")
            lines.append(f"- {title}\n  URL: {url}\n  {body}")
        return "\n".join(lines) if lines else "No results found."


def fetch_page(url, max_chars=3000):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = resp.text
        # very basic strip of tags for a lightweight fetch
        import re
        text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        return f"Failed to fetch {url}: {e}"