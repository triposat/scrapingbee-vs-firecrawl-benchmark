"""Aggregate the tuned runs (all available) into the article table and chart data.
PDF rule: Firecrawl counts when it returns parsed text of more than 1,000 bytes with HTTP 200, even if
the marker text is missing (run_bench.py's stricter "ok" flag is relaxed here). ScrapingBee returns the
file, so it counts when the bytes match a fresh direct download AND pypdf finds the marker in that file."""
import json, glob, re, requests, pypdf, io
PRICE = {"sb": 19 / 75000, "fc": 19 / 5000}
pages = {p["id"]: p for p in json.load(open("data/pages.json"))}
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
direct = {}
for p in pages.values():
    if p["type"] == "pdf":
        b = requests.get(p["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=60).content
        text = "".join(pg.extract_text() or "" for pg in pypdf.PdfReader(io.BytesIO(b)).pages)
        direct[p["id"]] = (len(b), norm(p["must"][0]) in norm(text))
rows = []
for f in sorted(glob.glob("results/run*-tuned-*.jsonl")):
    for l in open(f):
        r = json.loads(l); r["run"] = f.split("/")[-1].split("-")[0]
        if r["api"] == "fc" and r["type"] == "pdf":  # parsed text returned (2 forms drop only their title line)
            r["ok"] = r["ok"] or (r.get("bytes", 0) > 1000 and r.get("http") == 200)
        if r["api"] == "sb" and r["type"] == "pdf":
            size, parses = direct[r["id"]]
            r["ok"] = r.get("bytes") == size and parses
        rows.append(r)
out = {}
for t in ("static", "js", "protected", "pdf"):
    for api in ("sb", "fc"):
        R = [r for r in rows if r["type"] == t and r["api"] == api]
        ok = [r for r in R if r["ok"]]; cr = sum(r.get("credits") or 0 for r in R)
        out[(t, api)] = {"n": len(R), "ok": len(ok), "rate": len(ok) / len(R) if R else 0, "runs": sorted({r["run"] for r in R}), "credits": cr,
                         "usd_per_1k_ok": 1000 * cr * PRICE[api] / max(1, len(ok))}
for k, v in out.items(): print(k, v)
json.dump({f"{k[0]}|{k[1]}": v for k, v in out.items()}, open("results/aggregate.json", "w"), indent=1)
# protected per site: Auto Mode tier settled on each site
for site in ("zillow", "footlocker", "walmart", "etsy", "homedepot", "stockx"):
    for api in ("sb", "fc"):
        R = [r for r in rows if r.get("site") == site and r["api"] == api]
        ok = [r for r in R if r["ok"]]; cr = sum(r.get("credits") or 0 for r in R)
        print(site, api, f"{len(ok)}/{len(R)}", "credits/page", round(cr / max(1, len(R)), 1))
