# Deployment Information

## Public URL

https://optimistic-compassion-production-057e491a.up.railway.app

## Platform

Railway. Source: branch `main`, thư mục `/06-lab-complete`. Agent chạy
từ Dockerfile và kết nối với Redis trong cùng project. Public domain
trỏ tới cổng `8080`. Healthcheck trên Railway dùng `/health`.

## Environment variables

- `PORT`: Railway cấp, giá trị quan sát trong log là `8080`.
- `ENVIRONMENT`: `production`.
- `REDIS_URL`: tham chiếu tới `Redis.REDIS_URL` trong project.
- `AGENT_API_KEY`: đặt trong Railway Variables.

## Test commands

```bash
(
  BASE='https://optimistic-compassion-production-057e491a.up.railway.app'
  read -rs -p 'Railway API key: ' AGENT_API_KEY
  printf '\n'
  curl -sS -o /dev/null -w 'GET /health: %{http_code}\n' "$BASE/health"
  curl -sS -o /dev/null -w 'GET /ready: %{http_code}\n' "$BASE/ready"
  curl -sS -o /dev/null -w 'POST /ask without key: %{http_code}\n' \
    "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
  curl -sS -o /dev/null -w 'POST /ask with key: %{http_code}\n' \
    "$BASE/ask" -H 'Content-Type: application/json' \
    -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
)
```

Kết quả quan sát theo thứ tự: `200`, `200`, `401`, `200`.

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
