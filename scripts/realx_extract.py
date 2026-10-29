"""AI extraction on 15 real product pages (Etsy, Zillow, Walmart), scored against JSON-LD / page-data prices."""
import json, os, re, time, concurrent.futures as cf, requests
SB, FC = os.environ["SB_KEY"], os.environ["FC_KEY"]
T = json.load(open("results/real-extraction/truth.json"))
AI = {"name": "the main product or property name on the page", "price": {"description": "the current price of the main product or property, number only", "type": "number"}}
SCHEMA = {"type": "object", "properties": {"name": {"type": "string", "description": AI["name"]}, "price": {"type": "number", "description": AI["price"]["description"]}}, "required": ["name", "price"]}
def sb(t):
    r = requests.get("https://app.scrapingbee.com/api/v1/", params={"url": t["url"], "mode": "auto", "max_cost": "75", "ai_extract_rules": json.dumps(AI)}, headers={"Authorization": f"Bearer {SB}"}, timeout=180)
    try: d = r.json()
    except Exception: d = {"error": r.text[:200]}
    return {"api": "sb", "id": t["id"], "got": d, "credits": int(r.headers.get("Spb-cost", 0))}
def fc(t):
    for _ in range(6):
        r = requests.post("https://api.firecrawl.dev/v2/scrape", json={"url": t["url"], "maxAge": 0, "formats": [{"type": "json", "schema": SCHEMA}]}, headers={"Authorization": f"Bearer {FC}"}, timeout=180)
        if r.status_code != 429: break
        time.sleep(20)
    d = r.json().get("data") or {}
    return {"api": "fc", "id": t["id"], "got": d.get("json") or {"error": str(r.json())[:200]}, "credits": (d.get("metadata") or {}).get("creditsUsed", 0)}
with cf.ThreadPoolExecutor(4) as ex: res = list(ex.map(lambda a: a[0](a[1]), [(f, t) for t in T for f in (sb, fc)]))
norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
truth = {t["id"]: t["truth"][0] for t in T}
for r in res:
    tr = truth[r["id"]]; g = r["got"]
    try: r["price_ok"] = abs(float(g.get("price")) - tr["price"]) < 0.011
    except Exception: r["price_ok"] = False
    got_name = norm(g.get("name", "")) if isinstance(g, dict) and "error" not in g else ""
    r["name_ok"] = bool(got_name) and (got_name[:20] in norm(tr["name"]) or norm(tr["name"])[:20] in got_name)
json.dump(res, open("results/real-extraction/extract_results.json", "w"), indent=1)
for api in ("sb", "fc"):
    R = [r for r in res if r["api"] == api]
    print(api, "price right", sum(r["price_ok"] for r in R), "/", len(R), "name right", sum(r["name_ok"] for r in R), "credits", sum(r["credits"] or 0 for r in R))
    for r in R:
        if not r["price_ok"]: print("   MISS", r["id"], "got", r["got"].get("price") if isinstance(r["got"], dict) else r["got"], "truth", truth[r["id"]]["price"])
