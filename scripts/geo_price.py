"""Does the exit country change the price you get? Steam prices games by the visitor's country."""
import json, os, re, time, html as H, requests
SB, FC = os.environ["SB_KEY"], os.environ["FC_KEY"]
URL = "https://store.steampowered.com/app/413150/"
def price(h):
    m = re.search(r'class="game_purchase_price price"[^>]*>\s*([^<]+?)\s*<', h or "")
    return H.unescape(m.group(1)).strip() if m else None
out = []
for rnd in (1, 2):
    for cc in ("id", "de"):
        r = requests.get("https://app.scrapingbee.com/api/v1/", params={"url": URL, "premium_proxy": "true", "render_js": "false", "country_code": cc},
                         headers={"Authorization": f"Bearer {SB}"}, timeout=120)
        out.append({"round": rnd, "api": "sb", "asked": cc.upper(), "status": r.status_code, "credits": int(r.headers.get("Spb-cost", 0)), "price": price(r.text)})
        for _ in range(5):
            f = requests.post("https://api.firecrawl.dev/v2/scrape", json={"url": URL, "formats": ["rawHtml"], "maxAge": 0, "location": {"country": cc.upper()}},
                              headers={"Authorization": f"Bearer {FC}"}, timeout=120)
            if f.status_code != 429: break
            time.sleep(20)
        x = f.json().get("data") or {}
        out.append({"round": rnd, "api": "fc", "asked": cc.upper(), "status": f.status_code, "credits": (x.get("metadata") or {}).get("creditsUsed"), "price": price(x.get("rawHtml"))})
        for o in out[-2:]: print(o)
json.dump(out, open("geo-price.json", "w"), indent=1)
