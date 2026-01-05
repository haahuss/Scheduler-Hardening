#!/bin/bash

export A=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
export B=bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb

curl -s -X POST http://localhost:8000/tournaments \
  -H "X-User-Id: $A" -H "Content-Type: application/json" \
  -d '{"name":"A tourney","teams":[{"name":"A1"},{"name":"A2"}],"venues":[{"name":"Gym"}],"time_windows":[{"start_ts":"2027-01-05T18:00:00+00:00","end_ts":"2027-01-05T19:00:00+00:00","venue_id":null}]}' | jq .


curl -s http://localhost:8000/tournaments -H "X-User-Id: $A" | jq .
curl -s http://localhost:8000/tournaments -H "X-User-Id: $B" | jq .
