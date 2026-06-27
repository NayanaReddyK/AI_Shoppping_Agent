import json

text = """[{"store": "Noise", "title": "NoiseFit Twist Go Smartwatch", "price": "₹1,399"}, {"store": "Amazon", "title": "Noise NoiseFit Twist Go Smartwatch", "price": "₹1,499"}]
[
  {"store": "Noise", "title": "NoiseFit Twist Go Smartwatch", "price": "₹1,399"}
]"""

try:
    raw_competitors = json.loads(text)
    print("Parsed successfully first time.")
except json.JSONDecodeError as e:
    if "Extra data" in str(e):
        try:
            raw_competitors = json.loads(text[:e.pos])
            print("Successfully recovered using e.pos!")
            print(raw_competitors)
        except Exception as inner_e:
            print(f"Inner Parse Error: {inner_e}")
    else:
        print(f"JSON Decode Error: {e}")
except Exception as e:
    print(f"JSON Parse Error: {e}")
