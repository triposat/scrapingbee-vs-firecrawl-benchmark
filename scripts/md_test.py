"""Markdown quality: same 10 pages through ScrapingBee return_page_markdown and Firecrawl markdown.
Ground truth from a direct fetch: sentences from the main content (recall), headings, and table rows.
Usage: uv run python md_test.py truth|sb|fc|score"""
import json, os, re, sys, time, random
import requests
from bs4 import BeautifulSoup
SB, FC = os.environ.get("SB_KEY"), os.environ.get("FC_KEY")
PAGES = ["https://en.wikipedia.org/wiki/Web_scraping", "https://en.wikipedia.org/wiki/List_of_HTTP_status_codes",
         "https://docs.python.org/3/library/urllib.robotparser.html", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/403",
         "https://www.rfc-editor.org/rfc/rfc9309.html", "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
         "https://quotes.toscrape.com/page/1/", "https://github.com/scrapy/scrapy", "https://www.python-httpx.org/quickstart/",
         "https://www.scrapethissite.com/pages/forms/"]
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

def truth():
    out = {}; random.seed(7)
    for u in PAGES:
        soup = BeautifulSoup(requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text, "lxml")
        for el in soup.select("nav, footer, header, script, style"): el.decompose()
        main = soup.select_one("main, article, #mw-content-text, [role=main]") or soup.body
        sents = [s for p in main.select("p, li, td") for s in re.split(r"(?<=[.!?])\s+", p.get_text(" ", strip=True)) if len(s.split()) >= 8]
        picks = random.sample(sents, min(5, len(sents)))
        out[u] = {"recall": [" ".join(s.split()[2:8]) for s in picks],
                  "h": len(main.select("h1,h2,h3,h4,h5,h6")), "tr": len(main.select("tr"))}
    json.dump(out, open("results/md_truth.json", "w"), indent=1); print({u: (v["h"], v["tr"]) for u, v in out.items()})

def fetch(api):
    out = {}
    for u in PAGES:
        if api == "sb":
            r = requests.get("https://app.scrapingbee.com/api/v1/", params={"url": u, "return_page_markdown": "true", "render_js": "false"}, headers={"Authorization": f"Bearer {SB}"}, timeout=180)
            out[u] = {"md": r.text if r.ok else "", "credits": int(r.headers.get("Spb-cost", 0))}
        else:
            for _ in range(6):
                r = requests.post("https://api.firecrawl.dev/v2/scrape", json={"url": u, "maxAge": 0}, headers={"Authorization": f"Bearer {FC}"}, timeout=180)
                if r.status_code != 429: break
                time.sleep(20)
            d = r.json().get("data") or {}
            out[u] = {"md": d.get("markdown", ""), "credits": (d.get("metadata") or {}).get("creditsUsed")}
        print(api, u, len(out[u]["md"]), out[u]["credits"], flush=True)
    json.dump(out, open(f"results/md_{api}.json", "w"), indent=1)

def score():
    T = json.load(open("results/md_truth.json")); rows = []
    for api in ("sb", "fc"):
        D = json.load(open(f"results/md_{api}.json"))
        for u in PAGES:
            md = D[u]["md"]; nm = norm(md); t = T[u]
            rows.append({"api": api, "page": u.split("//")[1][:40],
                         "recall": sum(norm(s) in nm for s in t["recall"]), "recall_n": len(t["recall"]),
                         "headings": len(re.findall(r"^#{1,6} ", md, re.M)) + len(re.findall(r"^[^\n|*#>-][^\n]*\n(?:=+|-+)[ \t]*$", md, re.M)), "h_true": t["h"],
                         "table_rows": len(re.findall(r"^\|.*\|\s*$", md, re.M)), "tr_true": t["tr"],
                         "credits": D[u]["credits"]})
    json.dump(rows, open("results/md_scores.json", "w"), indent=1)
    for r in rows: print(r)
    for api in ("sb", "fc"):
        R = [r for r in rows if r["api"] == api]
        print(api, "recall", sum(r["recall"] for r in R), "/", sum(r["recall_n"] for r in R),
              "headings", sum(r["headings"] for r in R),
              "tables", sum(r["table_rows"] for r in R), "credits", sum((r["credits"] or 0) for r in R))

if __name__ == "__main__":
    {"truth": truth, "sb": lambda: fetch("sb"), "fc": lambda: fetch("fc"), "score": score}[sys.argv[1]]()
