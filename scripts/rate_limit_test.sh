#!/usr/bin/env bash

for i in $(seq 1 80); do
  curl -s http://localhost:8000/health | jq .
done
