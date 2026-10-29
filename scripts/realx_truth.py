"""Ground truth for real-page extraction: fetch product HTML via ScrapingBee Auto Mode and read price/name from JSON-LD."""
import json, os, re, sys, concurrent.futures as cf, requests
SB = os.environ["SB_KEY"]
P = [p for p in json.load(open("data/pages.json")) if p.get("site") in ("walmart", "etsy", "zillow")]
def ld(h):
    out = []
    for b in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', h, re.S):
        try: d = json.loads(b)
        except Exception: continue
        stack = d if isinstance(d, list) else [d]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if "offers" in x and x.get("name"):
                    o = x["offers"]; o = o[0] if isinstance(o, list) else o
                    if isinstance(o, dict):
                        price = o.get("price") or o.get("lowPrice")
                        if price is not None: out.append({"name": x["name"], "price": float(str(price).replace(",", "")), "currency": o.get("priceCurrency")})
                stack += [v for v in x.values() if isinstance(v, (dict, list))]
            elif isinstance(x, list): stack += x
    return out
def go(p):
    r = requests.get("https://app.scrapingbee.com/api/v1/", params={"url": p["url"], "mode": "auto", "max_cost": "75"}, headers={"Authorization": f"Bearer {SB}"}, timeout=180)
    open(f"results/real-extraction/{p['id']}.html", "w").write(r.text)
    return {"id": p["id"], "url": p["url"], "status": r.status_code, "credits": int(r.headers.get("Spb-cost", 0)), "truth": ld(r.text)[:3]}
with cf.ThreadPoolExecutor(5) as ex: res = list(ex.map(go, P))
json.dump(res, open("results/real-extraction/truth.json", "w"), indent=1)
for r in res: print(r["id"], r["status"], r["credits"], r["truth"][:1])
print("credits", sum(r["credits"] for r in res))
