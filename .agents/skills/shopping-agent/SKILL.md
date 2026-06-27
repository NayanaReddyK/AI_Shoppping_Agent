---
name: shopping-agent
version: 2.0.0
description: >
  Autonomous ReAct agent that accepts an e-commerce product URL, extracts the
  live price via a sandboxed MCP browser client, fetches real-time competitor
  prices using Gemini 1.5 with Google Search Grounding, filters outliers, persists
  results to MongoDB Atlas, and returns a structured BUY NOW / WAIT recommendation
  with supporting price evidence.
entry_point: skills/shopping_agent.py
runtime: python3.10+
dependencies: requirements.txt
requires_node: true   # MCP browser server runs via npx
---

# AI Shopping Agent — Skill Reference

## 1. Purpose

This skill coordinates the full price intelligence pipeline for Indian e-commerce products. It is designed to be invoked by an autonomous agent or called directly via the FastAPI endpoint `POST /api/analyze`.

**Input:** A single e-commerce product URL (string)  
**Output:** A structured JSON object (see Section 6)

---

## 2. Environment Requirements

The following environment variables must be present in `.env` before the skill can run:

| Variable | Required | Description |
|---|---|---|
| `MONGO_URI` | Yes | MongoDB Atlas connection string |
| `GEMINI_API_KEY` | Yes | Primary Gemini API key |
| `GEMINI_API_KEY_2` ... `_N` | Optional | Additional keys for round-robin load balancing |
| `GROQ_API_KEY` | Yes | Groq API key for LLaMA-3 inference |

Node.js must be installed and available on PATH — the MCP browser server is launched via `npx mcp-server-fetch-typescript`.

---

## 3. Project Structure (Skill-Relevant Files)

```
Project/
├── backend/
│   ├── server.py          # FastAPI app — exposes POST /api/analyze
│   ├── db.py              # MongoDB client, schema models, cache logic
│   └── api_balancer.py    # Round-robin Gemini key rotation
├── skills/
│   ├── shopping_agent.py  # THIS SKILL — ReAct loop orchestrator
│   └── scraper_skill.py   # Price extraction logic and fallback chain
├── .agents/
│   └── skills/
│       └── shopping-agent/
│           └── SKILL.md   # This file
```

---

## 4. ReAct Loop — Step-by-Step Workflow

The agent executes the following steps in order. Each step has defined inputs, outputs, and failure behaviour.

---

### Step 1 — Cache Check

**Module:** `backend/db.py` → `get_cached_result(url)`  
**What it does:** Queries the `url_cache` MongoDB collection for an existing result where:
- `url` matches the input exactly
- `timestamp` is within the last 3600 seconds (1 hour)

**Returns:**
- `dict` — full cached result object (see Section 6) if a valid cache entry exists
- `None` — if no entry exists or the entry is stale

**On cache hit:** Skip Steps 2–5 entirely. Return cached result directly to caller.  
**On cache miss:** Continue to Step 2.

---

### Step 2 — Fetch Page HTML

**Module:** `skills/scraper_skill.py` → `fetch_html_via_mcp(url: str) -> str`  
**What it does:** Launches the MCP browser client (`mcp-server-fetch-typescript` via `npx`) in a sandboxed context and fetches the full rendered HTML of the target product page.

**Signature:**
```python
async def fetch_html_via_mcp(url: str) -> str:
    """
    Args:
        url (str): Full product page URL (e.g. https://www.amazon.in/dp/B09XYZ)
    Returns:
        str: Raw HTML content of the page
    Raises:
        MCPConnectionError: If the MCP server fails to launch or times out
        ScrapingError: If the page returns a non-200 status or is blocked
    """
```

**Failure behaviour:**
- If MCP server fails to start → raise `MCPConnectionError`, abort pipeline, return error response
- If page is bot-blocked (returns CAPTCHA or 403) → raise `ScrapingError`, return error response with `"error": "page_blocked"`
- Timeout is 30 seconds; exceeded → raise `TimeoutError`

---

### Step 3 — Extract Product Price

**Module:** `skills/scraper_skill.py` → `extract_price(html: str, url: str) -> dict`  
**What it does:** Attempts price extraction using a three-tier fallback chain, in order:

**Tier 1 — CSS Selectors**
Targets known price element IDs/classes for major Indian retailers:
- Amazon: `#priceblock_ourprice`, `#priceblock_dealprice`, `.a-price-whole`
- Flipkart: `._30jeq3`, `._16Jk6d`
- Croma / Vijay Sales / Reliance Digital: common `[data-price]` and `.price` patterns

**Tier 2 — JSON-LD Schema Parsing**
Parses `<script type="application/ld+json">` blocks for `Product` schema with `offers.price`.

**Tier 3 — Groq / LLaMA-3 Heuristic**
If Tiers 1 and 2 return nothing, sends the raw HTML (truncated to 8000 tokens) to `llama-3.3-70b-versatile` on Groq with the prompt:
> "Extract the current selling price of the product from this HTML. Return only the numeric price in INR as a float. If you cannot find it, return null."

**Signature:**
```python
async def extract_price(html: str, url: str) -> dict:
    """
    Args:
        html (str): Raw HTML from fetch_html_via_mcp
        url  (str): Original product URL (used to select retailer-specific selectors)
    Returns:
        {
            "price": float,          # e.g. 45999.0
            "currency": "INR",
            "method": str,           # "css_selector" | "json_ld" | "llm_heuristic"
            "product_name": str      # Best-effort product title extracted from <title> or og:title
        }
    Raises:
        ExtractionError: If all three tiers fail to find a price
    """
```

**Failure behaviour:**
- All three tiers fail → raise `ExtractionError`, return error response with `"error": "price_not_found"`
- Groq quota exceeded → log warning, raise `ExtractionError` (do not retry with a different model)

---

### Step 4 — Fetch Competitor Prices

**Module:** `skills/shopping_agent.py` → `fetch_competitor_prices(product_name: str) -> list`  
**What it does:** Calls Gemini 1.5 Flash (`gemini-2.5-flash-lite`) with Google Search Grounding enabled. The query is dynamically constructed as:
> "Current price of {product_name} on Amazon India, Flipkart, Croma, Vijay Sales, Reliance Digital. List each store and price in INR."

The API key used is selected by `api_balancer.py` using round-robin rotation across all configured `GEMINI_API_KEY_*` values.

**Signature:**
```python
async def fetch_competitor_prices(product_name: str) -> list[dict]:
    """
    Args:
        product_name (str): Product title from Step 3 extraction result
    Returns:
        list of dicts, e.g.:
        [
            {"store": "Amazon", "price": 44999.0, "url": "https://..."},
            {"store": "Flipkart", "price": 45500.0, "url": "https://..."},
            {"store": "Croma", "price": 47000.0, "url": null},
        ]
        Note: "url" may be null if Gemini Search Grounding does not return a direct link.
    Raises:
        GeminiError: If all API keys are quota-exhausted or the request fails
    """
```

**Failure behaviour:**
- All Gemini keys quota-exhausted → raise `GeminiError`, return partial result with `"competitor_prices": []` and `"warning": "competitor_lookup_failed"`
- Gemini returns an empty or unparseable response → return empty list, proceed to Step 5 with source price only

---

### Step 5 — Filter Outliers & Find Cheapest Deal

**Module:** `skills/shopping_agent.py` → `find_cheapest_deal(prices: list[dict]) -> dict`  
**What it does:** Applies a statistical median filter to the competitor price list to remove anomalous values (fraudulent listings, out-of-stock placeholders, data errors), then identifies the cheapest verified source.

**Filter logic:**
1. Extract all `price` floats from the input list
2. Compute median `m` of the price list
3. Discard any price where `abs(price - m) > 0.4 * m` (i.e. more than 40% from median)
4. From the remaining prices, return the entry with the lowest price

**Signature:**
```python
def find_cheapest_deal(prices: list[dict]) -> dict:
    """
    Args:
        prices (list[dict]): Output from fetch_competitor_prices
                             Each dict must have at minimum: {"store": str, "price": float}
    Returns:
        {
            "store": str,       # e.g. "Flipkart"
            "price": float,     # e.g. 43999.0
            "url": str | null,
            "filtered_count": int  # how many entries were removed by the median filter
        }
    Raises:
        ValueError: If prices list is empty or all entries are filtered out
    """
```

**Failure behaviour:**
- Empty input list → return `None`, skip cheapest deal section in final response
- All entries filtered → return `None` with `"warning": "all_prices_filtered"`

---

### Step 6 — Generate Recommendation

**Module:** `skills/shopping_agent.py` → `generate_recommendation(source_price, cheapest, history) -> str`  
**What it does:** Compares the current source price against the cheapest competitor price and the historical price average from MongoDB to produce a `BUY NOW` or `WAIT` verdict.

**Decision logic:**
| Condition | Verdict |
|---|---|
| Source price ≤ cheapest competitor price AND source price ≤ historical average | `BUY NOW` |
| Cheapest competitor is more than 3% cheaper than source price | `WAIT — better price at {store}` |
| Source price > historical average by more than 5% | `WAIT — price is above average` |
| Insufficient history (< 3 records) | `BUY NOW — insufficient history to compare` |

---

### Step 7 — Persist to MongoDB

**Module:** `backend/db.py`  
**What it does:** Writes to two collections:

**Collection: `price_history`**
```json
{
  "url": "string",
  "product_name": "string",
  "source_price": 45999.0,
  "currency": "INR",
  "cheapest_store": "string",
  "cheapest_price": 43999.0,
  "competitor_prices": [...],
  "recommendation": "string",
  "extraction_method": "css_selector | json_ld | llm_heuristic",
  "timestamp": "2026-06-27T10:30:00Z"
}
```

**Collection: `url_cache`**
```json
{
  "url": "string",
  "result": { ...full response object... },
  "timestamp": "2026-06-27T10:30:00Z"
}
```

Cache TTL is enforced at query time (Step 1), not via a MongoDB TTL index — the document is not automatically deleted.

---

## 5. Error Response Format

When any step raises an unrecoverable error, the pipeline returns:

```json
{
  "success": false,
  "error": "error_code_string",
  "message": "Human-readable description",
  "url": "original input url",
  "timestamp": "ISO8601 timestamp"
}
```

Known error codes: `page_blocked`, `price_not_found`, `mcp_connection_failed`, `competitor_lookup_failed`, `database_error`

---

## 6. Success Response Format

```json
{
  "success": true,
  "url": "string",
  "product_name": "string",
  "source_price": 45999.0,
  "currency": "INR",
  "extraction_method": "css_selector | json_ld | llm_heuristic",
  "competitor_prices": [
    { "store": "Amazon", "price": 44999.0, "url": "string | null" },
    { "store": "Flipkart", "price": 45500.0, "url": "string | null" }
  ],
  "cheapest": {
    "store": "Amazon",
    "price": 44999.0,
    "url": "string | null",
    "filtered_count": 1
  },
  "recommendation": "WAIT — better price at Amazon",
  "historical_average": 46200.0,
  "cache_hit": false,
  "timestamp": "2026-06-27T10:30:00Z"
}
```

---

## 7. Known Limitations

- JavaScript-rendered SPAs may not return complete HTML via the MCP fetch client
- Gemini Search Grounding quality degrades for generic or ambiguous product names
- Cache is URL-exact — the same product on a different URL is treated as a new query
- Free-tier Groq and Gemini quotas limit throughput; the key balancer mitigates but does not eliminate this
- The median filter requires at least 2 competitor prices to be meaningful; with only 1 result, no filtering occurs

---

## 8. Utility Scripts

| Script | Command | Purpose |
|---|---|---|
| `seed_db.py` | `python scripts/seed_db.py` | Insert 500+ sample price history records |
| `view_db.py` | `python scripts/view_db.py` | Generate `debug/price_history_report.md` |
| `clear_cache.py` | `python scripts/clear_cache.py` | Flush all `url_cache` documents |