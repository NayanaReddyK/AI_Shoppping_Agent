import sys
import os

# Dynamically resolve root path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

import json
import asyncio
import re
from backend.db import get_price_history, save_extracted_prices
from skills.scraper_skill import fetch_html_via_mcp, extract_data_with_groq
from backend.api_balancer import get_groq_client, get_gemini_client
from google.genai import types

def find_cheapest_deal(results):
    cheapest = None
    min_price = float('inf')
    for r in results:
        p_str = str(r.get("price", ""))
        # Clean price string (e.g. ₹63,749 -> 63749.0)
        p_num_str = "".join(c for c in p_str if c.isdigit() or c == '.')
        if p_num_str:
            try:
                price_val = float(p_num_str)
                if price_val < min_price and price_val > 0:
                    min_price = price_val
                    cheapest = r
            except:
                pass
    return cheapest

async def run_agentic_loop(session, provided_url: str, base_store: str) -> dict:
    """
    The True Agentic ReAct Loop powered by Groq (LLaMA3).
    """
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    groq_client = get_groq_client()
    if not groq_client:
        return {"error": "No GROQ_API_KEY found in .env."}
        
    gemini_client = get_gemini_client()
    if not gemini_client:
        return {"error": "No GEMINI_API_KEY found in .env. Hybrid Search requires Gemini."}
    
    agent_state = {
        "url": provided_url,
        "base_store": base_store,
        "product_name": "Unknown",
        "results": [],
        "history": {}
    }

    groq_tools = [
        {
            "type": "function",
            "function": {
                "name": "fetch_product_data",
                "description": "CRITICAL: Call this FIRST. Scrapes the provided URL using an MCP headless browser to extract the exact product name and base price.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to scrape"},
                        "store_name": {"type": "string", "description": "The store name"}
                    },
                    "required": ["url", "store_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_competitors",
                "description": "Call this SECOND. Uses Google Search to find competitor prices for the exact product.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_name": {"type": "string", "description": "The exact product name to search for"}
                    },
                    "required": ["product_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "final_recommendation",
                "description": "Call this THIRD and LAST. Use this when you have gathered all necessary data and are ready to provide the final shopping recommendation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recommendation_text": {"type": "string", "description": "Your detailed shopping recommendation based on current and historical prices"},
                        "action": {"type": "string", "description": "BUY NOW or WAIT"}
                    },
                    "required": ["recommendation_text", "action"]
                }
            }
        }
    ]

    system_prompt = f"""
    You are an Autonomous AI Shopping Agent. Your mission is to analyze the user's URL: {provided_url} from {base_store}.
    You are not a simple text generator. You are a True Agent. You MUST actively use your tools to accomplish the mission.
    
    You MUST execute your mission in this exact sequential loop:
    1. Call 'fetch_product_data' to securely extract the identity of the product from the URL. (Use store_name "{base_store}" and url "{provided_url}")
    2. Read the result of 'fetch_product_data'. YOU MUST NOW MANDATORILY call 'search_competitors' with the exact product name. DO NOT skip this step under any circumstances. You cannot give a final recommendation without finding competitors first.
    3. Synthesize all the data (the primary price, competitor prices, and historical_price_baselines) and call 'final_recommendation'.
    
    CRITICAL DECISION GUIDELINES FOR 'final_recommendation':
    - You MUST read the `mathematically_cheapest_deal` object provided in the tool response. This contains the absolute lowest price sorted by Python.
    - Identify the e-commerce store name and price from this `mathematically_cheapest_deal` object and state both clearly in your final recommendation_text.
    - Compare this cheapest deal price against `historical_price_baselines`:
      - If the cheapest deal price is equal to or less than the `all_time_lowest_price` (or within 5% of it), you MUST set the action to "BUY NOW".
      - If the cheapest deal price is higher than the `average_price`, you MUST set the action to "WAIT" (because the current price is inflated).
      - If there is no historical database baseline (e.g., 'New product' or 'No historical data available'), compare the primary store price with competitor prices: if the primary store has the lowest or equal price, recommend "BUY NOW". If a competitor store is cheaper, recommend "WAIT" (or buy from the cheaper competitor instead).
    
    If a tool fails, you must still try to call 'search_competitors' with whatever product name you can guess, before calling 'final_recommendation'. Do NOT output plain text unless it's to describe your thoughts before calling a tool. Always prefer calling tools.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Begin your investigation. Remember to call your tools!"}
    ]

    print("\n[AGENT] Starting autonomous ReAct loop on GROQ...")

    for loop_count in range(10): # Failsafe loop limit
        try:
            response = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=groq_tools,
                tool_choice="auto",
                temperature=0.2
            )
        except Exception as e:
            error_msg = str(e).upper()
            if "RATE_LIMIT" in error_msg or "429" in error_msg:
                return {"error": "Groq API Limit Reached. Please try again later."}
            return {"error": f"Groq API Error: {str(e)}"}
            
        message = response.choices[0].message
        # Need to convert the Groq message object to a dict to append
        message_dict = {"role": "assistant"}
        if message.content: message_dict["content"] = message.content
        if message.tool_calls:
            message_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                } for tc in message.tool_calls
            ]
        messages.append(message_dict)

        if not message.tool_calls:
            print("[AGENT] No tools called. Agent said:", message.content)
            messages.append({"role": "user", "content": "You must use your tools to complete the mission. Please call the appropriate tool next, or call final_recommendation if you are done."})
            continue
            
        finished = False
        final_rec = None
        
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments)
            except:
                args = {}
                
            print(f"  [AGENT ACTION] Decided to call tool: {name}")
            
            result = {}
            if name == "fetch_product_data":
                html = await fetch_html_via_mcp(session, args.get("url", provided_url))
                if html:
                    data = await extract_data_with_groq(html, args.get("store_name", base_store), args.get("url", provided_url))
                    if data and "error" not in data.get("title", "").lower() and data.get("title") != "Not found":
                        if data.get("price") is None or str(data.get("price")).lower() in ["null", "none", ""]:
                            data["price"] = "Price not listed"
                            
                        # Add URL to primary scraped product
                        data["url"] = args.get("url", provided_url)
                        agent_state["product_name"] = data["title"]
                        # Clear existing results to prevent duplicates if Groq calls this tool multiple times
                        agent_state["results"] = [r for r in agent_state["results"] if r.get("store") != data.get("store")]
                        agent_state["results"].append(data)
                        result = {"status": "success", "data": data}
                    else:
                        result = {"status": "error", "message": data.get("title", "Unknown error")}
                else:
                    result = {"status": "error", "message": "Failed to scrape URL."}
                    
            elif name == "search_competitors":
                product_name = args.get('product_name', agent_state['product_name'])
                prompt = f"""
                You are a Perplexity-style smart shopping assistant. Your goal is to find the current price of this product on other major Indian e-commerce platforms.
                
                Raw Product Title from Source: "{product_name}"
                Original Store: {base_store}
                
                CRITICAL SEARCH INSTRUCTION:
                The Raw Product Title provided above is extremely messy, SEO-stuffed, and specific to the Original Store. If you search for it exactly, you will find 0 competitors!
                BEFORE using the Google Search tool, you MUST identify the clean Core Product Entity (Brand + Model + Key Spec). 
                For example, if the raw title is 'Noise Twist Go Round dial Smartwatch with BT Calling, 1.39 Display...', your clean search query must be 'Noise Twist Go Smartwatch buy online India'.
                Do NOT search the raw title. ALWAYS search for the clean Core Product Entity.
                
                Use the Google Search tool to find the absolute best prices across legitimate Indian websites.
                You MUST find prices from at least 3-4 DIFFERENT stores. Do not stop after finding just one.
 
                CRITICAL INSTRUCTIONS:
                1. LEGITIMATE RETAILERS ONLY: Extract prices from ALL legitimate e-commerce retailers (e.g., Amazon, Flipkart, Croma, Reliance Digital, Vijay Sales, Tata CLiQ, Myntra, Nykaa, JioMart, Headphone Zone, and official brand stores like Apple, Samsung, Sony, JBL, {base_store}).
                2. STRICT BLACKLIST: You MUST IGNORE ALL price aggregators, review sites, and sketchy importers. Completely IGNORE: Smartprix, Buyhatke, 91mobiles, Gadgets360, Cashify, MySmartPrice, FoneZone, Ubuy, Mahavir Mobile, India Today, NDTV.
                3. BANNED PRICES: If the search result says "EMI", "Wholesale", "null", or doesn't show a clear number, DO NOT include that store in your array! Skip it entirely.
                4. ACCESSORY FILTER: Ensure the price matches the actual requested product. Do NOT include cheap accessories (like silicone cases, ear tips, or chargers). If a price is suspiciously low (e.g., ₹13 for a ₹700 item), it is an accessory. IGNORE IT.
                
                Return strictly JSON array: [{{"store": "Store/Brand Name", "title": "Exact Product Title on that site", "price": "Price in INR", "url": "Direct URL link to the product page to buy it"}}]
                Do NOT use markdown code blocks like ```json. Return ONLY the raw JSON string.
                """
                try:
                    # SPAWN GEMINI EXCLUSIVELY FOR SEARCH WITH ROBUST RETRY/FALLBACK!
                    max_retries = 3
                    backoff_delay = 1.5
                    text = ""
                    
                    for attempt in range(max_retries):
                        try:
                            # On third attempt, try a different model (gemini-2.5-flash) to bypass model-specific capacity spikes
                            model_to_use = 'gemini-2.5-flash' if attempt == max_retries - 1 else 'gemini-2.5-flash-lite'
                            
                            search_resp = await gemini_client.aio.models.generate_content(
                                model=model_to_use,
                                contents=prompt,
                                config=types.GenerateContentConfig(
                                    tools=[{"google_search": {}}],
                                    temperature=0.0
                                )
                            )
                            text = search_resp.text.strip()
                            break  # Success!
                        except Exception as e:
                            print(f"[RETRY WARNING] Gemini search attempt {attempt + 1} failed: {e}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(backoff_delay * (attempt + 1))
                            else:
                                raise e
                    
                    # Clean up markdown code blocks if the model included them
                    cleaned_text = text.strip()
                    if cleaned_text.startswith("```json"):
                        cleaned_text = cleaned_text[7:]
                    elif cleaned_text.startswith("```"):
                        cleaned_text = cleaned_text[3:]
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-3]
                    cleaned_text = cleaned_text.strip()
                    
                    # Bulletproof JSON extraction using native JSON mode and extra data trimming
                    try:
                        raw_competitors = json.loads(cleaned_text)
                    except json.JSONDecodeError as e:
                        if "Extra data" in str(e):
                            try:
                                raw_competitors = json.loads(cleaned_text[:e.pos])
                            except Exception as inner_e:
                                with open("search_debug.txt", "w", encoding="utf-8") as f:
                                    f.write(f"Inner Parse Error: {inner_e}\n\nRAW TEXT:\n{text}")
                                raw_competitors = []
                        else:
                            with open("search_debug.txt", "w", encoding="utf-8") as f:
                                f.write(f"JSON Decode Error: {e}\n\nRAW TEXT:\n{text}")
                            raw_competitors = []
                    except Exception as e:
                        with open("search_debug.txt", "w", encoding="utf-8") as f:
                            f.write(f"JSON Parse Error: {e}\n\nRAW TEXT:\n{text}")
                        raw_competitors = []
                        
                    competitors = []
                    for c in raw_competitors:
                        price_val = c.get("price")
                        if price_val and str(price_val).lower() not in ["null", "none", "", "emi", "wholesale", "not listed"]:
                            if any(char.isdigit() for char in str(price_val)):
                                competitors.append(c)
                    
                    with open("search_out.txt", "w", encoding="utf-8") as f:
                        f.write(json.dumps(competitors, indent=2))

                    if isinstance(competitors, list) and len(competitors) > 0:
                        # DEDUPLICATE: Prevent Google from returning 2 Amazon listings, 
                        # and prevent duplicating the primary store we already scraped!
                        # We use re.sub to remove all spaces so "Tatacliq" matches "Tata CLiQ"
                        existing_stores = {re.sub(r'\s+', '', r.get("store", "").strip().lower()) for r in agent_state["results"]}
                        deduped_competitors = []
                        for comp in competitors:
                            store_name_lower = re.sub(r'\s+', '', comp.get("store", "").strip().lower())
                            
                            # Python-level blacklist for known bad actors (price aggregators/news)
                            bad_stores = ["smartprix", "buyhatke", "91mobiles", "gadgets360", "cashify", "mysmartprice", "fonezone", "ubuy", "mahavir", "indiatoday", "ndtv", "review", "news", "gsmarena"]
                            if any(bad in store_name_lower for bad in bad_stores):
                                continue

                            # Standardize 'Apple' and 'Apple.com' as the same store
                            if "apple" in store_name_lower:
                                store_name_lower = "apple"
                            if "amazon" in store_name_lower:
                                store_name_lower = "amazon"
                                
                            if store_name_lower and store_name_lower not in existing_stores:
                                existing_stores.add(store_name_lower)
                                deduped_competitors.append(comp)

                        # Filter out extreme low outliers (accessories) using median
                        if len(deduped_competitors) > 0:
                            import statistics
                            
                            valid_prices = []
                            for r in agent_state["results"] + deduped_competitors:
                                p_str = str(r.get("price", ""))
                                p_num_str = re.sub(r'[^0-9.]', '', p_str)
                                if p_num_str:
                                    try:
                                        valid_prices.append(float(p_num_str))
                                    except:
                                        pass
                                        
                            if len(valid_prices) >= 3:
                                median_price = statistics.median(valid_prices)
                                filtered_competitors = []
                                for comp in deduped_competitors:
                                    p_str = str(comp.get("price", ""))
                                    p_num_str = re.sub(r'[^0-9.]', '', p_str)
                                    if p_num_str:
                                        try:
                                            price_val = float(p_num_str)
                                            # Drop if price is less than 30% of the median
                                            if price_val >= (0.3 * median_price):
                                                filtered_competitors.append(comp)
                                        except:
                                            filtered_competitors.append(comp)
                                    else:
                                        filtered_competitors.append(comp)
                                deduped_competitors = filtered_competitors

                        agent_state["results"].extend(deduped_competitors)
                        
                        # Load and save MongoDB pricing baselines BEFORE LLM recommendation
                        if agent_state["product_name"] != "Unknown":
                            print("[PYTHON] Auto-saving results to DB...")
                            save_extracted_prices(agent_state["product_name"], agent_state["results"])
                            print("[PYTHON] Auto-fetching history from DB...")
                            agent_state["history"] = get_price_history(agent_state["product_name"], "")

                        result = {
                            "status": "success", 
                            "competitors_found": deduped_competitors,
                            "historical_price_baselines": agent_state["history"],
                            "mathematically_cheapest_deal": find_cheapest_deal(agent_state["results"])
                        }
                    else:
                        result = {"status": "failed", "message": "No competitors found in the search results."}
                except Exception as e:
                    print(f"\n[CRITICAL ERROR] Gemini search crashed! Reason: {repr(e)}\n")
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        result = {"status": "error", "message": "API_LIMIT_REACHED"}
                    else:
                        result = {"status": "error", "message": str(e)}
                    
            elif name == "final_recommendation":
                # BULLETPROOF SAFEGUARD: Did it actually run search_competitors?
                has_searched = any("competitors_found" in str(r) for r in messages if r.get("role") == "tool")
                if not has_searched and len(agent_state["results"]) <= 1:
                    result = {"status": "error", "message": "CRITICAL RULE VIOLATION: You attempted to call final_recommendation without calling search_competitors first. You MUST call search_competitors to find market prices before concluding."}
                    finished = False
                else:
                    final_rec = {
                        "Analysis": args.get("recommendation_text", ""),
                        "Action": args.get("action", "WAIT")
                    }
                    finished = True
                    result = {"status": "success", "message": "Mission complete."}
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
            
            # If search hit the Gemini API limit, gracefully fail the entire loop
            if result.get("message") == "API_LIMIT_REACHED":
                return {"error": "Gemini Search API Limit Reached. Please try again later."}
            
        if finished:
            print("[AGENT] ReAct Loop complete!")
            return {
                "product_name": agent_state["product_name"],
                "extracted_data": {
                    "product": agent_state["product_name"],
                    "stores": agent_state["results"]
                },
                "history_data": agent_state["history"],
                "recommendation": final_rec
            }
            
        print("  [AGENT SYSTEM] Returning tool results to the Groq Brain...")
        
    return {"error": "Agent hit maximum loops without concluding. It got stuck."}
