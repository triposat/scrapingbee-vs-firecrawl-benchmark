"""ScrapingBee vs Firecrawl benchmark runner.
Usage: uv run python run_bench.py <run_label> <config: default|tuned> [api: sb|fc|both]
Writes results/<run_label>-<config>-<api>.jsonl, one line per page, plus raw bodies in raw/.
"""
import json, os, re, sys, time, math, hashlib, threading, concurrent.futures as cf
import requests

SB_KEY, FC_KEY = os.environ["SB_KEY"], os.environ["FC_KEY"]
CONCURRENCY = 2  # Firecrawl free plan allows 2 browsers; use the same on ScrapingBee
BLOCK_MARKERS = ["captcha-delivery.com", "px-captcha", "perimeterx", "Just a moment...", "cf-chl", "challenge-platform",
                 "Access Denied", "Pardon Our Interruption", "Request unsuccessful", "_Incapsula_", "kpsdk", "verify you are human",
                 "Robot or human?", "Press & Hold", "are you a robot", "unusual traffic"]

def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())

def judge(page, body, is_markdown):
    """Content-based success: expected text present and no block page. Status codes alone don't count."""
    if not body: return False, "empty"
    head = body[:20000]
    hit = [m for m in BLOCK_MARKERS if m.lower() in head.lower()]
    nb = norm(body)
    if page["type"] == "protected":
        toks = page["slug_tokens"]
        found = sum(norm(t) in nb for t in toks)
        need = max(1, math.ceil(0.6 * len(toks)))
        if found >= need and len(body) > 1500 and not (hit and len(body) < 30000):
            return True, f"tokens {found}/{len(toks)}"
        return False, f"tokens {found}/{len(toks)} len {len(body)} block {hit[:2]}"
    if page["type"] == "pdf":
        if body.startswith("%PDF"):
            return None, "raw PDF bytes returned"  # delivered, not parsed: scored separately
        ok = norm(page["must"][0]) in nb
        return ok, "text found" if ok else "marker missing"
    ok = all(norm(m) in nb for m in page["must"])
    if ok and page.get("rendered") and not is_markdown and 'class="quote"' not in body:
        return False, "quote text only inside <script>, page not rendered"
    return ok, "markers found" if ok else "marker missing"

def sb_call(page, config):
    params = {"url": page["url"]}
    if config == "tuned":
        # Settings per page type, as ScrapingBee's docs describe them:
        # static and PDF: no browser; JS pages: browser plus a selector wait; protected: Auto Mode with a cost cap
        if page["type"] in ("static", "pdf"): params["render_js"] = "false"
        elif page["type"] == "js": params["wait_for"] = ".quote"
        else: params.update({"mode": "auto", "max_cost": "75"})
        if page["type"] != "pdf": params["return_page_markdown"] = "true"
    try:
        for attempt in range(2):  # one retry on transport errors only
            try:
                r = requests.get("https://app.scrapingbee.com/api/v1/", params=params,
                                 headers={"Authorization": f"Bearer {SB_KEY}"}, timeout=180); break
            except requests.ConnectionError:
                if attempt: raise
                time.sleep(5)
    except Exception as e:
        return {"api": "sb", "ok": False, "why": f"client error {e}", "credits": 0}
    is_pdf = r.content[:4] == b"%PDF"
    body = "%PDF(binary)" if is_pdf else r.text
    ok, why = judge(page, body, config == "tuned") if r.status_code == 200 else (False, f"api {r.status_code}: {r.text[:120]}")
    return {"api": "sb", "ok": ok, "why": why, "http": r.status_code,
            "credits": int(r.headers.get("Spb-cost", 0) or 0), "auto_cost": r.headers.get("Spb-auto-cost"),
            "target_status": r.headers.get("Spb-initial-status-code"), "bytes": len(r.content), "body": body}

def fc_call(page, config):
    payload = {"url": page["url"], "formats": ["markdown"]}
    if config == "tuned":
        payload.update({"proxy": "auto", "maxAge": 0})
        if "js-delayed" in page["url"]: payload["waitFor"] = 12000
    for attempt in range(6):
        try:
            r = requests.post("https://api.firecrawl.dev/v2/scrape", json=payload,
                              headers={"Authorization": f"Bearer {FC_KEY}"}, timeout=180)
        except requests.ConnectionError:  # transport error to the API: wait and retry
            time.sleep(10); continue
        except Exception as e:
            return {"api": "fc", "ok": False, "why": f"client error {e}", "credits": 0}
        if r.status_code == 429:  # rate limited: wait and retry
            wait = int(r.headers.get("Retry-After", 0) or 0) or 15 * (attempt + 1)
            time.sleep(wait); continue
        break
    try: d = r.json()
    except Exception: d = {}
    data = d.get("data") or {}
    md = data.get("markdown") or ""
    meta = data.get("metadata") or {}
    ok, why = judge(page, md, True) if r.status_code == 200 and d.get("success") else (False, f"api {r.status_code}: {str(d.get('error') or r.text)[:160]}")
    return {"api": "fc", "ok": ok, "why": why, "http": r.status_code, "credits": meta.get("creditsUsed", 0),
            "target_status": meta.get("statusCode"), "proxy_used": meta.get("proxyUsed"), "cache": meta.get("cacheState"),
            "bytes": len(md), "body": md}

def main():
    label, config = sys.argv[1], sys.argv[2]
    apis = {"both": ["sb", "fc"]}.get(sys.argv[3] if len(sys.argv) > 3 else "both", [sys.argv[3] if len(sys.argv) > 3 else None])
    pages = json.load(open("data/pages.json"))
    os.makedirs("results", exist_ok=True); os.makedirs("raw", exist_ok=True)  # full response bodies, not committed
    fn = {"sb": sb_call, "fc": fc_call}
    def worker(api, page):
        res = fn[api](page, config)
        body = res.pop("body", "") or ""
        h = hashlib.sha1(f"{label}{config}{api}{page['id']}".encode()).hexdigest()[:10]
        open(f"raw/{label}-{config}-{api}-{page['id']}-{h}.txt", "w").write(body)
        res.update({"id": page["id"], "type": page["type"], "site": page.get("site"), "url": page["url"], "ts": time.time()})
        return res
    for api in apis:
        out = open(f"results/{label}-{config}-{api}.jsonl", "w")
        with cf.ThreadPoolExecutor(CONCURRENCY) as ex:
            for res in ex.map(lambda p: worker(api, p), pages):
                out.write(json.dumps(res) + "\n"); out.flush()
                print(api, res["id"], res["ok"], res["why"][:70], res.get("credits"), res.get("cache") or res.get("auto_cost") or "", flush=True)
        out.close()

if __name__ == "__main__":
    main()
