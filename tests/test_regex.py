import json
import re

text = """```json
[
  {
    "store": "Apple",
    "title": "AirPods 4",
    "price": "12900.00"
  },
  {
    "store": "Reliance Digital",
    "title": "Apple AirPods 4",
    "price": "12900.00"
  }
]
```"""

match = re.search(r'\[.*\]', text, re.DOTALL)
if match:
    clean_json_str = match.group(0)
    print("Clean JSON STR:")
    print(clean_json_str)
    try:
        raw_competitors = json.loads(clean_json_str)
        competitors = []
        for c in raw_competitors:
            price_val = c.get("price")
            if price_val and str(price_val).lower() not in ["null", "none", "", "emi", "wholesale", "not listed"]:
                if any(char.isdigit() for char in str(price_val)):
                    competitors.append(c)
        print("Final competitors:", competitors)
    except Exception as e:
        print("JSON parse error:", e)
else:
    print("No regex match.")
