import re
import urllib.parse
import urllib.request

def web_search(query, n=5):
    try:
        q = urllib.parse.quote(query)
        req = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?q={q}",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        results = re.findall(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', html)
        out = [f"- {t.strip()}: {h}" for h, t in results[:n]]
        return "\n".join(out) if out else "No results"
    except Exception as e:
        return f"Search error: {e}"
