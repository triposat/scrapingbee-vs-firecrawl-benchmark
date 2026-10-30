"""Ground truth for real-page extraction: fetch product HTML via ScrapingBee Auto Mode and read the price and name the page
declares about itself, from JSON-LD (Etsy, Zillow) or Walmart's Next.js page data."""
import json, os, re, sys, concurrent.futures as cf, requests
from structured_price import walmart_price
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
def next_data(h):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    if not m: return []
    try: name = json.loads(m.group(1))["props"]["pageProps"]["initialData"]["data"]["product"]["name"]
    except (KeyError, TypeError, ValueError): return []
    price = walmart_price(h)
    return [{"name": name, "price": price, "currency": "USD", "source": "__NEXT_DATA__ priceInfo.currentPrice"}] if price is not None else []
def go(p):
    r = requests.get("https://app.scrapingbee.com/api/v1/", params={"url": p["url"], "mode": "auto", "max_cost": "75"}, headers={"Authorization": f"Bearer {SB}"}, timeout=180)
    open(f"results/real-extraction/{p['id']}.html", "w").write(r.text)
    return {"id": p["id"], "url": p["url"], "status": r.status_code, "credits": int(r.headers.get("Spb-cost", 0)), "truth": (ld(r.text) or next_data(r.text))[:3]}
with cf.ThreadPoolExecutor(5) as ex: res = list(ex.map(go, P))
json.dump(res, open("results/real-extraction/truth.json", "w"), indent=1)
for r in res: print(r["id"], r["status"], r["credits"], r["truth"][:1])
print("credits", sum(r["credits"] for r in res))
