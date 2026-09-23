import subprocess
import time
import json
import urllib.request

# Start Chrome with remote debugging
cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "http://localhost:8000"
]

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2)

try:
    # Query CDP endpoints
    res = urllib.request.urlopen("http://localhost:9222/json").read().decode('utf-8')
    tabs = json.loads(res)
    print("Found tabs:", len(tabs))
    for t in tabs:
        print("Tab:", t.get("title"), t.get("url"), t.get("webSocketDebuggerUrl"))
finally:
    proc.terminate()
