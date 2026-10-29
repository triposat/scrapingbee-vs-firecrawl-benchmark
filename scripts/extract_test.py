"""Structured extraction on 20 books.toscrape.com product pages, scored against an answer key parsed from the HTML.
Usage: uv run python extract_test.py key|sb_css|sb_ai|fc_json"""
import json, os, re, sys, time, concurrent.futures as cf
import requests
from bs4 import BeautifulSoup
SB, FC = os.environ.get("SB_KEY"), os.environ.get("FC_KEY")
WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

def key():
    s = requests.Session(); out = []
    cat = BeautifulSoup(s.get("https://books.toscrape.com/catalogue/page-2.html").text, "lxml")
    for a in cat.select("article.product_pod h3 a"):
        u = "https://books.toscrape.com/catalogue/" + a["href"]
        d = BeautifulSoup(s.get(u).content, "lxml")
        rows = {r.th.text: r.td.text for r in d.select("table.table tr")}
        out.append({"url": u, "title": d.h1.text.strip(), "price": float(rows["Price (incl. tax)"].lstrip("£Â")),
                    "stock": int(re.search(r"\d+", rows["Availability"]).group()), "upc": rows["UPC"],
                    "rating": WORDS[d.select_one("p.star-rating")["class"][1]]})
    json.dump(out, open("results/extract_key.json", "w"), indent=1); print(len(out), out[0])

SCHEMA = {"type": "object", "properties": {"title": {"type": "string"}, "price": {"type": "number", "description": "price including tax, number only"},
          "stock": {"type": "integer", "description": "number of copies available"}, "upc": {"type": "string"},
          "rating": {"type": "integer", "description": "star rating from 1 to 5"}}, "required": ["title", "price", "stock", "upc", "rating"]}
CSS = {"title": "h1", "price": "p.price_color", "stock": "p.availability", "upc": "table.table tr:nth-child(1) td",
       "rating": {"selector": "p.star-rating", "output": "@class"}}
AI = {"title": "book title", "price": {"description": "price including tax, number only", "type": "number"},
      "stock": {"description": "number of copies available", "type": "number"}, "upc": "UPC code",
      "rating": {"description": "star rating from 1 to 5", "type": "number"}}

def clean(rec):
    """Normalise CSS-selector output (raw strings) into typed fields. AI/JSON outputs pass through."""
    r = dict(rec)
    if isinstance(r.get("price"), str): r["price"] = float(re.sub(r"[^\d.]", "", r["price"]) or 0)
    if isinstance(r.get("stock"), str): r["stock"] = int((re.search(r"\d+", r["stock"]) or [0])[0])
    if isinstance(r.get("rating"), str): r["rating"] = WORDS.get(r["rating"].split()[-1], r["rating"])
    return r

def call(mode, u):
    t0 = time.time()
    if mode.startswith("sb"):
        p = {"url": u, "render_js": "false"}
        p["extract_rules" if mode == "sb_css" else "ai_extract_rules"] = json.dumps(CSS if mode == "sb_css" else AI)
        r = requests.get("https://app.scrapingbee.com/api/v1/", params=p, headers={"Authorization": f"Bearer {SB}"}, timeout=180)
        rec = r.json() if r.status_code == 200 else {}
        return rec, int(r.headers.get("Spb-cost", 0)), time.time() - t0
    for _ in range(6):
        r = requests.post("https://api.firecrawl.dev/v2/scrape", headers={"Authorization": f"Bearer {FC}"}, timeout=180,
                          json={"url": u, "maxAge": 0, "formats": [{"type": "json", "schema": SCHEMA}]})
        if r.status_code != 429: break
        time.sleep(20); t0 = time.time()
    d = (r.json().get("data") or {})
    return d.get("json") or {}, (d.get("metadata") or {}).get("creditsUsed", 0), time.time() - t0

def run(mode):
    K = json.load(open("results/extract_key.json"))
    with cf.ThreadPoolExecutor(2) as ex:
        res = list(ex.map(lambda k: call(mode, k["url"]), K))
    fields = ["title", "price", "stock", "upc", "rating"]; right = 0; rows = []
    for k, (rec, cost, _) in zip(K, res):
        rec = clean(rec)
        ok = {f: (str(rec.get(f)).strip() == str(k[f]) if f in ("title", "upc") else rec.get(f) is not None and float(rec.get(f)) == float(k[f])) for f in fields}
        right += sum(ok.values()); rows.append({"url": k["url"], "got": rec, "ok": ok, "credits": cost})
    json.dump(rows, open(f"results/extract_{mode}.json", "w"), indent=1)
    wrong = [(r["url"].split("/")[-2], f, r["got"].get(f)) for r in rows for f, v in r["ok"].items() if not v]
    print(mode, f"fields correct {right}/{len(K)*len(fields)}", "credits", sum(r["credits"] for r in rows),
          "wrong:", wrong[:8])

if __name__ == "__main__":
    key() if sys.argv[1] == "key" else run(sys.argv[1])
