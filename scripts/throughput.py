"""Wall-clock time for 100 static pages at a given concurrency (ScrapingBee, render_js=false)."""
import os, sys, time, requests, concurrent.futures as cf
from bs4 import BeautifulSoup
SB = os.environ["SB_KEY"]
urls = []
for n in range(1, 6):
    cat = BeautifulSoup(requests.get(f"https://books.toscrape.com/catalogue/page-{n}.html").text, "lxml")
    urls += ["https://books.toscrape.com/catalogue/" + a["href"] for a in cat.select("article.product_pod h3 a")]
def get(u):
    r = requests.get("https://app.scrapingbee.com/api/v1/", params={"url": u, "render_js": "false"}, headers={"Authorization": f"Bearer {SB}"}, timeout=120)
    return r.status_code, int(r.headers.get("Spb-cost", 0))
for c in map(int, sys.argv[1:]):
    t0 = time.time()
    with cf.ThreadPoolExecutor(c) as ex: res = list(ex.map(get, urls))
    print(f"concurrency {c}: {len(urls)} pages in {time.time()-t0:.1f}s, ok {sum(s == 200 for s, _ in res)}, credits {sum(x for _, x in res)}")
