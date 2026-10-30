"""Firecrawl's side of the geo tests rerun with proxy="enhanced". Firecrawl's docs list the enhanced proxy's locations as the US and the Netherlands.
Writes results/geo/geo-exit-fc-enhanced.json and results/geo/geo-price-fc-enhanced.json."""
import json, os, re, time, html as H, requests
FC = os.environ["FC_KEY"]
ECHO = "http://ip-api.com/json/?fields=countryCode,country,isp,query"
STEAM = "https://store.steampowered.com/app/413150/"
COUNTRIES = ["de", "jp", "br", "in", "kr", "za", "id", "ar"]
def scrape(url, cc):
    for _ in range(5):
        r = requests.post("https://api.firecrawl.dev/v2/scrape",
                          json={"url": url, "formats": ["rawHtml"], "maxAge": 0, "proxy": "enhanced", "location": {"country": cc.upper()}},
                          headers={"Authorization": f"Bearer {FC}"}, timeout=180)
        if r.status_code != 429: break
        time.sleep(20)
    x = r.json().get("data") or {}
    meta = x.get("metadata") or {}
    return r.status_code, x.get("rawHtml") or "", meta.get("creditsUsed"), meta.get("proxyUsed")
def echo(h):
    m = re.search(r'\{[^{}]*"countryCode"[^{}]*\}', h)
    return json.loads(m.group(0)) if m else {"raw": h[:120]}
def price(h):
    m = re.search(r'class="game_purchase_price price"[^>]*>\s*([^<]+?)\s*<', h)
    return H.unescape(m.group(1)).strip() if m else None
exits, prices = [], []
for rnd in (1, 2):
    for cc in COUNTRIES:
        st, h, cr, px = scrape(ECHO, cc)
        e = echo(h); exits.append({"round": rnd, "asked": cc.upper(), "status": st, "credits": cr, "proxy": px, "echo": e})
        print("exit", rnd, cc.upper(), "->", e.get("countryCode", e), "| proxy", px, "| credits", cr, flush=True)
    for cc in ("id", "de"):
        st, h, cr, px = scrape(STEAM, cc)
        prices.append({"round": rnd, "asked": cc.upper(), "status": st, "credits": cr, "proxy": px, "price": price(h)})
        print("price", rnd, cc.upper(), "->", price(h), "| proxy", px, "| credits", cr, flush=True)
os.makedirs("results/geo", exist_ok=True)
json.dump(exits, open("results/geo/geo-exit-fc-enhanced.json", "w"), indent=1)
json.dump(prices, open("results/geo/geo-price-fc-enhanced.json", "w"), indent=1)
