import json, os, re, urllib.request, urllib.parse, concurrent.futures as cf
K = os.environ["SB_KEY"]
Q = {
 "etsy": ["site:etsy.com/listing ceramic mug", "site:etsy.com/listing leather wallet"],
 "zillow": ["site:zillow.com/homedetails austin tx", "site:zillow.com/homedetails denver co"],
 "homedepot": ["site:homedepot.com/p cordless drill", "site:homedepot.com/p patio chair"],
 "stockx": ["site:stockx.com nike dunk low panda", "site:stockx.com new balance 550"],
 "footlocker": ["site:footlocker.com/product nike air force 1", "site:footlocker.com/product jordan 4"],
 "walmart": ["site:walmart.com/ip coffee maker", "site:walmart.com/ip air fryer"],
 "bestbuy": ["site:bestbuy.com/site headphones"],
}
pat = {"etsy": r"^https://www\.etsy\.com/listing/\d+", "zillow": r"^https://www\.zillow\.com/homedetails/", "homedepot": r"^https://www\.homedepot\.com/p/",
       "stockx": r"^https://stockx\.com/[a-z0-9-]+$", "footlocker": r"^https://www\.footlocker\.com/product/", "walmart": r"^https://www\.walmart\.com/ip/", "bestbuy": r"^https://www\.bestbuy\.com/site/.+\.p"}
def q(site, s):
    r = urllib.request.Request("https://app.scrapingbee.com/api/v1/fast_search?" + urllib.parse.urlencode({"search": s}), headers={"Authorization": f"Bearer {K}"})
    for attempt in range(3):
        try:
            d = json.load(urllib.request.urlopen(r, timeout=60)); break
        except Exception as e:
            print("retry", s, e); d = {}
    return site, [o["link"] for o in d.get("organic", []) if re.match(pat[site], o["link"])]
out = {}
with cf.ThreadPoolExecutor(8) as ex:
    for site, links in ex.map(lambda a: q(*a), [(s, x) for s, xs in Q.items() for x in xs]):
        out.setdefault(site, [])
        out[site] += [l for l in links if l not in out[site]]
json.dump(out, open("data/candidates.json", "w"), indent=1)
for k, v in out.items(): print(k, len(v), v[:3])
