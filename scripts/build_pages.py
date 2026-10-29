"""Build pages.json: URL list with ground-truth markers (fetched directly from unprotected sources)."""
import json, re, requests
from bs4 import BeautifulSoup
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (benchmark ground truth)"
pages = []
# 10 books + 10 quotes pages (static)
cat = BeautifulSoup(S.get("https://books.toscrape.com/catalogue/page-1.html").text, "lxml")
for a in cat.select("article.product_pod h3 a")[:10]:
    u = "https://books.toscrape.com/catalogue/" + a["href"]
    t = BeautifulSoup(S.get(u).text, "lxml").h1.text.strip()
    pages.append({"id": f"static-books-{len(pages)+1}", "type": "static", "url": u, "must": [t]})
for n in range(1, 11):
    u = f"https://quotes.toscrape.com/page/{n}/"
    q = BeautifulSoup(S.get(u).text, "lxml").select_one(".quote")
    pages.append({"id": f"static-quotes-{n}", "type": "static", "url": u,
                  "must": [q.select_one(".text").text.strip("“”")[:40], q.select_one(".author").text]})
# 20 JS pages: /js/ and /js-delayed/ (10 s delay)
for kind in ("js", "js-delayed"):
    for n in range(1, 11):
        u = f"https://quotes.toscrape.com/{kind}/page/{n}/"
        data = json.loads(re.search(r"var data = (\[.*?\]);\s*\n", S.get(u).text, re.S).group(1))
        pages.append({"id": f"{kind}-{n}", "type": "js", "url": u, "rendered": True,
                      "must": [data[0]["text"].strip("“”")[:40], data[0]["author"]["name"]]})
# 30 protected pages: 5 per site, robots.txt-allowed (see robots/)
STOP = {"the", "and", "for", "with", "set", "of", "in", "to", "a", "gift", "pc", "pack", "unit"}
c = json.load(open("data/candidates_allowed.json"))
for site in ("etsy", "zillow", "homedepot", "stockx", "footlocker", "walmart"):
    for u in c[site][:5]:
        path = u.rstrip("/").split("/")
        slug = {"etsy": path[-1], "zillow": path[-2], "homedepot": path[-2], "stockx": path[-1],
                "footlocker": path[-1].replace(".html", ""), "walmart": path[-2]}[site]
        toks = [t for t in re.split(r"[-_~]", slug) if len(t) >= 3 and t.lower() not in STOP and not t.isdigit()][:5]
        pages.append({"id": f"protected-{site}-{len(pages)%5+1}", "type": "protected", "site": site, "url": u, "slug_tokens": toks})
PDFS = [("https://www.irs.gov/pub/irs-pdf/fw9.pdf", "Request for Taxpayer"), ("https://www.irs.gov/pub/irs-pdf/fw4.pdf", "Employee's Withholding Certificate"),
        ("https://www.irs.gov/pub/irs-pdf/f1040.pdf", "Individual Income Tax Return"), ("https://www.irs.gov/pub/irs-pdf/fw8ben.pdf", "Certificate of Foreign Status"),
        ("https://www.irs.gov/pub/irs-pdf/fss4.pdf", "Application for Employer Identification Number"), ("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf", "Dummy PDF file"),
        ("https://arxiv.org/pdf/1706.03762", "Attention Is All You Need"), ("https://www.uscis.gov/sites/default/files/document/forms/i-9.pdf", "Employment Eligibility Verification"),
        ("https://pdfobject.com/pdf/sample.pdf", "This is a simple PDF"), ("https://www.orimi.com/pdf-test.pdf", "PDF Test File")]
for i, (u, m) in enumerate(PDFS, 1):
    pages.append({"id": f"pdf-{i}", "type": "pdf", "url": u, "must": [m]})
json.dump(pages, open("data/pages.json", "w"), indent=1)
from collections import Counter; print(Counter(p["type"] for p in pages), len(pages))
for p in pages[::9]: print(p["id"], p.get("must") or p.get("slug_tokens"))
