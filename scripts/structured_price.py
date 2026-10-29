"""Read the prices a product page declares about itself, for checking an extracted price.

Works on the full page HTML (ScrapingBee's default response, or Firecrawl's rawHtml format):
- JSON-LD: every offers.price / offers.lowPrice in application/ld+json blocks
- Walmart: the product's own price in the Next.js page data (not the first price on the page,
  which often belongs to a recommended item)

A page that lists variants can declare several prices. Match the offer for the variant you track
(its SKU, size, or URL), not just any declared price.

Usage: python structured_price.py page.html
"""
import json
import re
import sys


def jsonld_prices(html):
    prices = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                offers = item.get("offers")
                for offer in offers if isinstance(offers, list) else [offers]:
                    if isinstance(offer, dict):
                        price = offer.get("price", offer.get("lowPrice"))
                        if price is not None:
                            prices.append(float(str(price).replace(",", "")))
                stack.extend(v for v in item.values() if isinstance(v, (dict, list)))
    return prices


def walmart_price(html):
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return None
    try:
        product = json.loads(match.group(1))["props"]["pageProps"]["initialData"]["data"]["product"]
        return float(product["priceInfo"]["currentPrice"]["price"])
    except (KeyError, TypeError, ValueError):
        return None


def declared_prices(html):
    prices = jsonld_prices(html)
    own = walmart_price(html)
    return prices + ([own] if own is not None else [])


if __name__ == "__main__":
    print(declared_prices(open(sys.argv[1], encoding="utf-8", errors="ignore").read()))
