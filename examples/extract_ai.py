import json
import os

import requests

API_KEY = os.environ["SCRAPINGBEE_API_KEY"]

rules = {
    "title": "book title",
    "price": {"description": "price including tax, number only", "type": "number"},
    "in_stock": {"description": "number of copies available", "type": "number"},
    "upc": "UPC code from the product information table",
}

response = requests.get(
    "https://app.scrapingbee.com/api/v1/",
    headers={"Authorization": f"Bearer {API_KEY}"},
    params={
        "url": "https://books.toscrape.com/catalogue/sharp-objects_997/index.html",
        "render_js": "false",
        "ai_extract_rules": json.dumps(rules),
    },
    timeout=120,
)
response.raise_for_status()
print(json.dumps(response.json(), indent=2))
print("Credits used:", response.headers["Spb-cost"])
