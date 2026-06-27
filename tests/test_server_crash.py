import requests
import time
import subprocess
import os

print("Starting Uvicorn...")
proc = subprocess.Popen(["python", "-m", "uvicorn", "server:app", "--port", "8001"])
time.sleep(3) # Wait for startup

print("Sending POST request to /api/analyze...")
try:
    response = requests.post("http://127.0.0.1:8001/api/analyze", json={"product": "IEM earphones"})
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)
except Exception as e:
    print("Request failed:", e)
finally:
    proc.terminate()
