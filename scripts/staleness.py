"""Cache staleness on popular product pages: Firecrawl default (cache allowed) vs maxAge 0, same moment.
Price = Walmart's own page data (props.pageProps.initialData.data.product.priceInfo.currentPrice.price)."""
import json, os, re, time, datetime as dt, requests
FC = os.environ["FC_KEY"]
U = json.load(open("results/extra/popular-walmart-urls.json"))
def price(h):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h or "", re.S)
    try: return float(json.loads(m.group(1))["props"]["pageProps"]["initialData"]["data"]["product"]["priceInfo"]["currentPrice"]["price"])
    except Exception: return None
def fc(u, extra):
    for _ in range(6):
        r = requests.post("https://api.firecrawl.dev/v2/scrape", json={"url": u, "formats": ["rawHtml"], **extra}, headers={"Authorization": f"Bearer {FC}"}, timeout=180)
        if r.status_code != 429: break
        time.sleep(20)
    d = r.json(); x = d.get("data") or {}; m = x.get("metadata") or {}
    return {"ok": bool(d.get("success")), "cache": m.get("cacheState"), "cachedAt": m.get("cachedAt"), "credits": m.get("creditsUsed", 0), "price": price(x.get("rawHtml"))}
out = []
for u in U:
    now = dt.datetime.now(dt.timezone.utc)
    a = fc(u, {})
    row = {"url": u, "checked_at": now.isoformat(), "default": a}
    if a["cache"] == "hit":
        row["age_hours"] = round((now - dt.datetime.fromisoformat(a["cachedAt"].replace("Z", "+00:00"))).total_seconds() / 3600, 1)
        row["fresh"] = fc(u, {"maxAge": 0})
        row["price_changed"] = None if None in (a["price"], row["fresh"]["price"]) else a["price"] != row["fresh"]["price"]
    out.append(row)
    print(u.split("/ip/")[1][:40].ljust(40), a["cache"], row.get("age_hours"), a["price"], row.get("fresh", {}).get("price"), row.get("price_changed"), flush=True)
json.dump(out, open("results/extra/fc-cache-staleness.json", "w"), indent=1)
hits = [r for r in out if r["default"]["cache"] == "hit"]
print("hits", len(hits), "of", len(out), "| ages h:", sorted(r["age_hours"] for r in hits), "| price changed:", sum(1 for r in hits if r.get("price_changed")), "| compared:", sum(1 for r in hits if r.get("price_changed") is not None))
print("credits", sum(r["default"]["credits"] or 0 for r in out) + sum(r.get("fresh", {}).get("credits") or 0 for r in out))
