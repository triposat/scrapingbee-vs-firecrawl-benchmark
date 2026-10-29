"""Which country does each API's request actually exit from? ip-api.com echoes the caller's IP location."""
import json, os, re, time, concurrent.futures as cf, requests
SB, FC = os.environ["SB_KEY"], os.environ["FC_KEY"]
ECHO = "http://ip-api.com/json/?fields=countryCode,country,isp,query"
COUNTRIES = {"de": "in Firecrawl's list", "jp": "in Firecrawl's list", "br": "in Firecrawl's list", "in": "in Firecrawl's list",
             "kr": "not in Firecrawl's list", "za": "not in Firecrawl's list", "id": "not in Firecrawl's list", "ar": "not in Firecrawl's list"}
def parse(text):
    m = re.search(r'\{[^{}]*"countryCode"[^{}]*\}', text or "")
    return json.loads(m.group(0)) if m else {"raw": (text or "")[:120]}
def sb(cc):
    r = requests.get("https://app.scrapingbee.com/api/v1/", params={"url": ECHO, "premium_proxy": "true", "render_js": "false", "country_code": cc},
                     headers={"Authorization": f"Bearer {SB}"}, timeout=120)
    return {"api": "sb", "asked": cc.upper(), "status": r.status_code, "credits": int(r.headers.get("Spb-cost", 0)), "echo": parse(r.text)}
def fc(cc):
    for _ in range(5):
        r = requests.post("https://api.firecrawl.dev/v2/scrape", json={"url": ECHO, "formats": ["rawHtml"], "maxAge": 0, "location": {"country": cc.upper()}},
                          headers={"Authorization": f"Bearer {FC}"}, timeout=120)
        if r.status_code != 429: break
        time.sleep(20)
    d = r.json(); x = d.get("data") or {}
    return {"api": "fc", "asked": cc.upper(), "status": r.status_code, "credits": (x.get("metadata") or {}).get("creditsUsed"), "proxy": (x.get("metadata") or {}).get("proxyUsed"), "echo": parse(x.get("rawHtml"))}
jobs = [(f, cc) for cc in COUNTRIES for f in (sb, fc)]
with cf.ThreadPoolExecutor(2) as ex: res = list(ex.map(lambda a: a[0](a[1]), jobs))
json.dump(res, open("geo-exit.json", "w"), indent=1)
for r in res:
    print(r["api"], r["asked"], COUNTRIES[r["asked"].lower()].ljust(24), "->", r["echo"].get("countryCode", r["echo"]), r["echo"].get("isp", "")[:30], "| credits", r["credits"])
