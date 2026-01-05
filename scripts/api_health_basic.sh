# bash api_health_basic.sh
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8000/tournaments -H "X-User-Id: 11111111-1111-1111-1111-111111111111" | jq .
