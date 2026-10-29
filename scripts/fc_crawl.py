"""Firecrawl /v2/crawl of the same docs site, 20 pages, Markdown, fresh fetches."""
import json, os, time, requests
FC = os.environ["FC_KEY"]; H = {"Authorization": f"Bearer {FC}"}
t0 = time.time()
r = requests.post("https://api.firecrawl.dev/v2/crawl", headers=H, json={"url": "https://www.python-httpx.org/", "limit": 20, "sitemap": "include",
                  "scrapeOptions": {"formats": ["markdown"], "maxAge": 0}}, timeout=60).json()
print(r); job = r["id"]
while True:
    s = requests.get(f"https://api.firecrawl.dev/v2/crawl/{job}", headers=H, timeout=60).json()
    if s.get("status") in ("completed", "failed", "cancelled"): break
    time.sleep(3)
docs = s.get("data", [])
print("status", s.get("status"), "pages", len(docs), "creditsUsed", s.get("creditsUsed"), "wall s", round(time.time() - t0, 1))
json.dump(s, open("results/crawl_fc.json", "w"), indent=1)
print(sorted(d["metadata"].get("sourceURL") for d in docs)[:25])
print("total md chars", sum(len(d.get("markdown", "")) for d in docs))
