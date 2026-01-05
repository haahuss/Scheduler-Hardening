#!/usr/bin/python3
import requests, uuid, time

BASE="http://localhost:8000"
uid=str(uuid.uuid4())
h={"X-User-Id": uid}

# hammer a cheap endpoint
hits=0
for i in range(200):
    r=requests.get(f"{BASE}/tournaments", headers=h)
    if r.status_code == 429:
        print("✅ rate limit triggered at request", i+1)
        print("Body:", r.text[:200])
        break
    hits += 1
else:
    print("⚠️ never hit 429; hits=", hits)
