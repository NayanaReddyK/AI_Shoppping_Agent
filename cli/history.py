import random

def get_price_history(product_name: str, current_price_str: str) -> dict:
    """
    Mocks a Price History API (like Keepa) to provide historical context.
    In a paid production environment, this would hit an actual tracking database API.
    """
    print(f"\n[HISTORY PHASE] Fetching 6-month price history for '{product_name}'...")
    
    # Try to parse the current price roughly to generate realistic history
    try:
        # Strip everything except digits and decimal point
        clean_price = "".join(c for c in current_price_str if c.isdigit() or c == '.')
        current_price = float(clean_price)
    except:
        current_price = 50000.0 # Fallback
        
    # Generate a mock history
    lowest_price = current_price * random.uniform(0.7, 0.9)
    highest_price = current_price * random.uniform(1.1, 1.4)
    average_price = current_price * random.uniform(0.9, 1.1)
    
    history_data = {
        "all_time_lowest_price": round(lowest_price, 2),
        "all_time_highest_price": round(highest_price, 2),
        "6_month_average": round(average_price, 2),
        "status": "Currently at historically average prices" if current_price > lowest_price * 1.1 else "Currently near all-time low"
    }
    
    print("   Retrieved Historical Data API Response:")
    for k, v in history_data.items():
        print(f"    - {k}: {v}")
        
    return history_data
