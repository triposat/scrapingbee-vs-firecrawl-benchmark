"""Estimate your monthly ScrapingBee bill from a sample of your own URLs.

Each line of the input file is a URL, optionally the pages a month you expect
from that URL's domain, and optionally text that a usable page must contain:

    https://www.zillow.com/homedetails/221-Park-Ln-Austin-TX-78704/29458732_zpid/ 20000 Park Ln
    https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html 50000 A Light in the Attic

The script requests every URL once with Auto Mode. A response counts as usable
only when it has no block-page markers and contains the expected text, because a
block page can come back with HTTP 200. The projection uses cost per usable page:
every credit charged in the sample, divided by the usable pages. Tiers can vary
between requests to the same site, so sample several URLs per domain.

Usage (from the repository root): python scripts/estimate_cost.py urls.txt [--max-cost 75]
"""
import argparse
import collections
import os
import urllib.parse

import requests

PLANS = [("Hobby", 19, 75_000), ("Freelance", 49, 250_000), ("Startup", 99, 1_000_000),
         ("Business", 249, 3_000_000), ("Business+", 599, 8_000_000)]
BLOCK_MARKERS = ["captcha-delivery.com", "px-captcha", "just a moment...", "challenge-platform",
                 "access denied", "pardon our interruption", "verify you are human", "press & hold"]

parser = argparse.ArgumentParser()
parser.add_argument("urls")
parser.add_argument("--max-cost", default="75")
args = parser.parse_args()

volume, samples = {}, collections.defaultdict(list)
with open(args.urls) as f:
    for line in f:
        if not line.strip():
            continue
        url, *rest = line.split()
        pages = int(rest[0]) if rest and rest[0].isdigit() else 0
        expected = " ".join(rest[1:] if rest and rest[0].isdigit() else rest).lower()
        domain = urllib.parse.urlparse(url).netloc
        volume[domain] = max(volume.get(domain, 0), pages)
        response = requests.get(
            "https://app.scrapingbee.com/api/v1/",
            headers={"Authorization": f"Bearer {os.environ['SCRAPINGBEE_API_KEY']}"},
            params={"url": url, "mode": "auto", "max_cost": args.max_cost},
            timeout=180,
        )
        body = response.text.lower()
        usable = (response.status_code == 200
                  and not any(marker in body[:20_000] for marker in BLOCK_MARKERS)
                  and expected in body)
        samples[domain].append((usable, int(response.headers.get("Spb-cost", 0) or 0),
                                int(response.headers.get("Spb-auto-cost", 0) or 0)))

total = 0
print(f"{'domain':28} {'sampled':>7} {'usable':>6} {'tiers seen':>10} {'credits/usable':>14} {'pages/month':>11} {'credits/month':>13}")
for domain, rows in samples.items():
    usable = [r for r in rows if r[0]]
    charged = sum(r[1] for r in rows)
    per_page = charged / len(usable) if usable else 0
    credits = round(per_page * volume[domain])
    total += credits
    seen = f"{min(r[2] for r in usable)}-{max(r[2] for r in usable)}" if usable else "-"
    print(f"{domain:28} {len(rows):7} {len(usable):6} {seen:>10} {per_page:14.1f} {volume[domain]:11,} {credits:13,}")
    if len(usable) < len(rows):
        unbilled = sum(1 for r in rows if not r[0] and r[1] == 0)
        print(f"{'':28} {len(rows) - len(usable)} unusable sample(s), {unbilled} of them not billed")

print(f"\nEstimated credits a month: {total:,}")
fits = [p for p in PLANS if p[2] >= total]
if fits:
    name, price, credits = fits[0]
    print(f"Smallest plan that fits: {name} (${price}, {credits:,} credits, {total / credits:.0%} used)")
else:
    print("Above Business+: contact ScrapingBee for an Enterprise plan")
