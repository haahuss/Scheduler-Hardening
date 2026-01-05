#!/usr/bin/python3
import requests, uuid, json

BASE="http://localhost:8000"
uid=str(uuid.uuid4())
h={"X-User-Id": uid, "Content-Type": "application/json"}

# intentionally huge team list
payload={
  "name":"Big One",
  "teams":[{"name": f"T{i}"} for i in range(5000)],
  "venues":[{"name":"V1"}],
  "time_windows":[{"start_ts":"2027-01-05T18:00:00+00:00","end_ts":"2027-01-05T19:00:00+00:00","venue_id":None}]
}
r=requests.post(f"{BASE}/tournaments", headers=h, data=json.dumps(payload))
print("status:", r.status_code)
print("body:", r.text[:300])
