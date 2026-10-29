"""Which protected product pages declare a machine-readable price? Fetches the full HTML with
ScrapingBee Auto Mode and reads declared prices with structured_price.py.
Usage: python scripts/structured_price_scan.py [site ...]"""
import json, os, sys, concurrent.futures as cf, requests
sys.path.insert(0, "scripts")
from structured_price import jsonld_prices, walmart_price
SB = os.environ["SB_KEY"]
sites = set(sys.argv[1:])
P = [p for p in json.load(open("data/pages.json")) if p["type"] == "protected" and (not sites or p["site"] in sites)]
def go(p):
    r = requests.get("https://app.scrapingbee.com/api/v1/", params={"url": p["url"], "mode": "auto", "max_cost": "75"},
                     headers={"Authorization": f"Bearer {SB}"}, timeout=180)
    html = r.text if r.status_code == 200 else ""
    return {"id": p["id"], "site": p["site"], "status": r.status_code, "credits": int(r.headers.get("Spb-cost", 0)),
            "jsonld_prices": jsonld_prices(html)[:5], "page_data_price": walmart_price(html)}
with cf.ThreadPoolExecutor(5) as ex: res = list(ex.map(go, P))
out = f"results/extra/structured-price-scan-{'-'.join(sorted(sites)) or 'all'}.json"
json.dump(res, open(out, "w"), indent=1)
for r in res: print(r["id"], r["status"], r["credits"], r["jsonld_prices"], r["page_data_price"])
