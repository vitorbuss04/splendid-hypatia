import subprocess
import urllib.request
import json

def main():
    p = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True
    )
    token = None
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            token = line[9:]
            break
    
    if not token:
        print("Token not found")
        return

    req = urllib.request.Request(
        "https://api.github.com/repos/vitorbuss04/splendid-hypatia/issues?state=all&per_page=100",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "IssueLister"}
    )
    with urllib.request.urlopen(req) as resp:
        issues = json.loads(resp.read().decode())
    
    print(f"Total issues: {len(issues)}")
    for i in sorted(issues, key=lambda x: x["number"]):
        print(f"#{i['number']} [{i['state']}] {i['title']}")

if __name__ == "__main__":
    main()
