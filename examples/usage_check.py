import os

import requests

response = requests.get(
    "https://app.scrapingbee.com/api/v1/usage",
    headers={"Authorization": f"Bearer {os.environ['SCRAPINGBEE_API_KEY']}"},
    timeout=30,
)
response.raise_for_status()
usage = response.json()
left = usage["max_api_credit"] - usage["used_api_credit"]
share = left / usage["max_api_credit"]
print(f"{left:,} credits left ({share:.0%} of the plan)")
if share < 0.15:
    print("Under 15% left: upgrade or renew before the pipeline stops")
