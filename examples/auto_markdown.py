import json
import os

import requests

API_KEY = os.environ["SCRAPINGBEE_API_KEY"]

response = requests.get(
    "https://app.scrapingbee.com/api/v1/",
    headers={"Authorization": f"Bearer {API_KEY}"},
    params={
        "url": "https://quotes.toscrape.com/js/",
        "mode": "auto",
        "max_cost": "25",
        "js_scenario": json.dumps({"instructions": [{"wait_for": ".quote"}]}),
        "return_page_markdown": "true",
    },
    timeout=150,
)
response.raise_for_status()
first_quote = next(line for line in response.text.splitlines() if "by " in line)
print(first_quote)
print("Tier that worked (credits):", response.headers["Spb-auto-cost"])
print("Total credits charged:", response.headers["Spb-cost"])
