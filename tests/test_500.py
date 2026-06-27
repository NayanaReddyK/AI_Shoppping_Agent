import subprocess
import time
import requests
import sys
import threading

def start_server():
    print("Starting Uvicorn server on port 8005...")
    # Run server and capture output
    process = subprocess.Popen(["uvicorn", "server:app", "--port", "8005"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Give it 5 seconds to boot up
    time.sleep(5)
    
    print("Sending POST request to /api/analyze...")
    try:
        res = requests.post("http://127.0.0.1:8005/api/analyze", json={"url": "https://www.amazon.in/dp/B0CHX1W1XY"}, timeout=60)
        print("Status Code:", res.status_code)
        print("Response:", res.text[:500])
    except Exception as e:
        print("Request failed:", e)
        
    print("Killing server...")
    process.terminate()
    
    # Print server logs
    print("\n--- SERVER LOGS ---")
    out, _ = process.communicate()
    print(out)

if __name__ == "__main__":
    start_server()
