# ScrapingBee vs Firecrawl benchmark

A reproducible cost and success-rate test of two web scraping APIs, ScrapingBee and Firecrawl, on the same 100 public pages. Use it to check the numbers in the article [ScrapingBee vs Firecrawl: Which Web Scraping API Should You Use in 2026?](https://www.scrapingbee.com/blog/scrapingbee-vs-firecrawl/), to rerun the test on your own accounts, or to estimate what your own URLs would cost.

The benchmark was written for the ScrapingBee blog, so it isn't neutral. That's why every script, URL, and per-page verdict is here. The raw page bodies aren't published, because that content belongs to each site.

## Quick start

Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/triposat/scrapingbee-vs-firecrawl-benchmark.git
cd scrapingbee-vs-firecrawl-benchmark
cp .env.example .env   # add your API keys
set -a; source .env; set +a
uv sync
```

**Estimate your monthly ScrapingBee credits** from a sample of your own URLs. Each input line is a URL, the pages a month you expect from its domain, and text a usable page must contain (see `data/sample-urls.txt`):

```bash
uv run python scripts/estimate_cost.py data/sample-urls.txt
```

**Rerun the benchmark** on your own accounts. Live sites change, so your numbers will differ, and that's the point. Use a new run label so you don't overwrite the published runs, and move `results/run{1,2,3}-*.jsonl` aside first, because `aggregate.py` combines every `run*` file in `results/`:

```bash
uv run python scripts/run_bench.py run4 tuned both
uv run python scripts/aggregate.py
```

## Results (October 2026)

Each of the 80 static, JavaScript, protected, and PDF pages ran 3 times. Costs are per 1,000 successful pages at each $19 plan's credit price on October 28, 2026 ($0.000253 for ScrapingBee Hobby, $0.0038 for Firecrawl Hobby).

| Page type | ScrapingBee cost | Firecrawl cost | ScrapingBee success | Firecrawl success |
|---|---|---|---|---|
| Static | $0.25 | $3.80 | 60 of 60 | 60 of 60 |
| JavaScript | $1.27 | $3.80 | 60 of 60 | 60 of 60 |
| Protected | $7.27 | $3.80 | 89 of 90 | 90 of 90 |
| PDF | $0.25 | $14.44 | 29 of 30 | 30 of 30 |

On protected pages, Auto Mode used the 1-credit tier on Zillow and Foot Locker and the 10-credit tier on Walmart, so those 3 sites cost less on ScrapingBee. On Etsy, Home Depot, and StockX, Auto Mode moved to the 25- or 75-credit tier as each site required. The `auto_cost` field in each results file shows the tier for every request.

PDFs of 1 to 15 pages cost $0.25 per 1,000 successful files on ScrapingBee, which returns the original file, and $14.44 on Firecrawl, which converts each PDF to Markdown and bills per PDF page. The 20-page crawl succeeded on every page with both APIs. Weighting each page type by its number of pages, the cost per 1,000 successful pages across all 100 pages was $2.56 on ScrapingBee and $4.86 on Firecrawl. Without the PDFs, it was $2.82 on ScrapingBee and $3.80 on Firecrawl. The article covers the reasons and the trade-offs.

## What was tested

| Group | Pages | Source |
|---|---|---|
| Static | 20 | books.toscrape.com (10), quotes.toscrape.com (10) |
| JavaScript | 20 | quotes.toscrape.com/js/ (10), quotes.toscrape.com/js-delayed/ (10, quotes appear after 10 seconds) |
| Protected | 30 | 5 product or listing pages each from Etsy, Zillow, Home Depot, StockX, Foot Locker, and Walmart |
| PDF | 10 | IRS forms, a USCIS form, an arXiv paper, and three sample PDFs |
| Crawl | 20 | python-httpx.org, from its sitemap |

`data/pages.json` lists every URL with its success marker. `robots/` holds each protected site's robots.txt as fetched, and every protected URL was allowed for the `*` user agent. No page needs a login.

## Settings

Both APIs ran the 80 scraped pages at 2 concurrent requests, the limit of the free Firecrawl account used. The crawls ran separately. ScrapingBee's CLI ran at concurrency 20, and Firecrawl's /crawl job ran on the same account.

| Page type | ScrapingBee | Firecrawl |
|---|---|---|
| Static | `render_js=false`, `return_page_markdown=true` | Markdown, `maxAge: 0`, default `auto` proxy |
| JavaScript | `wait_for=.quote`, `return_page_markdown=true` | Markdown, `maxAge: 0`, `waitFor: 12000` on the delayed pages |
| Protected | `mode=auto`, `max_cost=75`, `return_page_markdown=true` | Markdown, `maxAge: 0`, default `auto` proxy |
| PDF | `render_js=false` | Markdown, `maxAge: 0` |

## Success rule

A page counts only when its expected text is in the response and the response isn't a block page (`scripts/run_bench.py`, function `judge`):

- Static and JavaScript pages: the first quote's text and author, or the book title, taken from a direct fetch. For HTML responses on JavaScript pages, the rendered `class="quote"` element must be present, because the raw page carries the quotes inside a script tag.
- Protected pages: at least 60% of the product-name or address words from the URL slug, more than 1,500 characters, and no challenge markers (DataDome, PerimeterX, Cloudflare, Akamai, Kasada, Incapsula strings). Markers are ignored in responses of 30,000 characters or more, because full product pages often load those vendors' scripts.
- PDFs: `scripts/aggregate.py` applies the PDF rule, so the `ok` field in the run files isn't final for PDFs. Firecrawl counts when it returns more than 1,000 bytes of parsed text, even if the marker text is missing (pdf-2 and pdf-8 drop their title line). ScrapingBee returns the file, which counts when its size matches a fresh direct download and pypdf finds the marker text in it. Because `aggregate.py` downloads each PDF again, a changed source PDF changes this result.

## Billing data

Credits come from ScrapingBee's `Spb-cost` response header and Firecrawl's `metadata.creditsUsed` field. Firecrawl's reported credits matched the drop in its account balance over the runs. Firecrawl rows that show `proxy_used: "stealth"` cost 1 credit, because Firecrawl bills its enhanced proxy at the same 1 credit as a basic request. The 80 scraped pages ran 3 times on 2026-10-26, and the 20-page crawl ran once. Costs are priced at each $19 plan's credit price ($0.000253 for ScrapingBee Hobby, $0.0038 for Firecrawl Hobby).

## Files

- `results/run{1,2,3}-tuned-{sb,fc}.jsonl`: one line per page with success, reason, credits, Auto Mode tier (`auto_cost`), and Firecrawl cache state.
- `results/aggregate.json`: totals by page type. `scripts/charts.py` draws the article's cost chart (the PNG in `results/`) from it.
- `results/extract_*.json`: structured extraction on 20 books.toscrape.com pages, scored against `extract_key.json`.
- `results/md_scores.json`: Markdown quality on 10 pages (sampled-sentence recall, headings, table rows, credits).
- `results/crawl_scrapingbee_manifest.json` (the manifest from the article's Example 3 CLI crawl) and `results/crawl_firecrawl_summary.json` (a summary of what `scripts/fc_crawl.py` writes to `results/crawl_fc.json`): the 20-page crawls. Each API fetched 20 URLs from the sitemap, and 16 are the same. ScrapingBee's set includes one image (`img/speakeasy.png`), and Firecrawl's includes a duplicate path (`//async/`). Each API was billed 1 credit per URL.
- `data/candidates_allowed.json`: candidate protected URLs from `scripts/find_urls.py` that each site's robots.txt in `robots/` allows. `scripts/build_pages.py` turns them into `data/pages.json`.

## Rerun every part

After the quick start, these commands rerun the main test, the extraction test, and the Markdown test. Move the published run files aside first, as in the quick start:

```bash
uv run python scripts/run_bench.py run4 tuned both
uv run python scripts/aggregate.py
uv run python scripts/extract_test.py key
uv run python scripts/extract_test.py sb_css
uv run python scripts/extract_test.py sb_ai
uv run python scripts/extract_test.py fc_json
uv run python scripts/md_test.py truth
uv run python scripts/md_test.py sb
uv run python scripts/md_test.py fc
uv run python scripts/md_test.py score
```

The scripts read `SB_KEY` and `FC_KEY`, and the examples and the estimator read `SCRAPINGBEE_API_KEY`. `.env.example` lists all three.

## Follow-up tests

- `scripts/staleness.py` → `results/extra/fc-cache-staleness.json`: 32 popular Walmart product URLs (31 unique) through Firecrawl's defaults. Each cache hit is compared with an uncached fetch of the same page, using the price from Walmart's page data. The 31 unique URLs got 5 cached copies, 1.7 to 41.1 hours old, and none had a different price. The file shows a 6th hit on the repeated Switch 2 URL. That copy was 0 hours old, created by this script's own fresh request a moment earlier, so it isn't counted.
- `scripts/realx_truth.py` and `scripts/realx_extract.py` → `results/real-extraction/`: AI extraction of name and price on 15 live product pages, scored against the price each page declares about itself. The pages are protected, so the ground truth was fetched through ScrapingBee on 2026-10-26. `realx_truth.py` reads JSON-LD (Etsy, Zillow). The Walmart rows come from Walmart's Next.js page data, read with `scripts/structured_price.py`. The extraction ran on 2026-10-29.
- `scripts/estimate_cost.py`: estimate your monthly ScrapingBee credits from a sample of your own URLs. A page counts as usable only with no block-page markers and with the expected text you supply on each input line. The projection divides every credit charged by the usable pages. Sample input is in `data/sample-urls.txt`, and its output is in `logs/estimate-cost-output.txt`.
- `scripts/throughput.py` → `logs/throughput.txt`: 100 books.toscrape.com pages on ScrapingBee at 5 and at 25 concurrent requests.
- `scripts/structured_price_scan.py` → `results/extra/structured-price-scan.json` (the script writes `structured-price-scan-all.json`): the machine-readable price (JSON-LD or Next.js page data) on the protected product pages. Etsy's JSON-LD contains HTML entities that the scan's JSON parser rejects, so Etsy's prices are taken from `results/real-extraction/truth.json`.
- `scripts/mcp_tool_tokens.py` → `results/mcp/` (the script writes `{name}-tools.json`): tokens in each MCP server's tool definitions (`o200k_base`).
- `scripts/structured_price.py`: reads the prices a page declares about itself (JSON-LD offers, and Walmart's own product price in its Next.js page data). Run it on the full page HTML. It matched all 15 ground-truth prices in `results/real-extraction/truth.json`. An earlier scan used a regex that took the first price in Walmart's page data, which often belongs to a recommended item. Those rows are marked in `structured-price-scan.json`, and the corrected values are in `structured-price-scan-walmart.json`.
- `logs/uuid-cache-test.txt`: httpbin.org/uuid through both APIs. ScrapingBee returned a new ID each time. Firecrawl's defaults returned the same cached ID twice, from a copy cached 10 minutes before the test.
- `scripts/geo_exit.py` → `results/geo/geo-exit-round{1,2}.json` (the script writes `geo-exit.json`, saved once per round): the exit country for 8 requested countries on ScrapingBee premium proxies and Firecrawl's default, checked with ip-api.com. `scripts/geo_fc_enhanced.py` → `results/geo/geo-exit-fc-enhanced.json` and `geo-price-fc-enhanced.json`: Firecrawl's side rerun with `proxy: "enhanced"`, its strongest proxy. `results/geo/screenshots/`: full-page 2× screenshots of the Steam page requested from Indonesia through each API (2026-10-29), the source of the article's geo image.
- `scripts/geo_price.py` → `results/geo/geo-price-stardew.json` (the script writes `geo-price.json`): Steam's regional price for Stardew Valley, requested for Indonesia and Germany on both APIs.

## Logs

Raw request and response output behind claims in the article. The single-request logs carry their date in the first lines. The example and estimator outputs are from October 2026 and have no header, so they match the article's output blocks exactly:

- `logs/blocked-request-not-charged.txt`: a Home Depot page requested without a premium proxy. The target's 403 came back as a 500 with `spb-cost: 0`.
- `logs/json-endpoint-vs-rendered.txt`: the same 10 quotes from quotes.toscrape.com's JSON endpoint (1 credit) and from the rendered page (5 credits).
- `logs/fast-search-sample.txt`: one Fast Search request, its result counts, and its cost (10 credits).
- `logs/antibot-probe.txt`: a direct request to each protected site's homepage, showing its anti-bot system.
- `logs/example-{1,2}-output.txt`, `logs/example-3-cli-crawl.txt`: the output of the article's three examples. Examples 1 and 2 are in `examples/`. Example 3 is the CLI command shown in the article.
- `logs/estimate-cost-output.txt`, `logs/throughput.txt`, `logs/uuid-cache-test.txt`: see the follow-up tests above.

## License

The code is released under the MIT License (see `LICENSE`). Scraped page content, screenshots, and robots.txt files belong to their owners and are included only as test evidence.
