**API Overview**
- **Service:** Proxy & HTTP checker (FastAPI)
- **Interactive docs:** `GET /docs` (Swagger UI), `GET /redoc` (ReDoc)
- **OpenAPI JSON:** `GET /openapi.json`

**How it works**
- Register servers (Squid proxies or HTTP/nginx) via CRUD endpoints. The service starts a background checker task per server which runs at the server's `interval` and stores the last 100 pings in a SQLite DB (`backend/data.db`).
- Squid check target is configured through the environment variable `SQUID_HTTP_TARGET` (default `https://httpbin.org/get`).

**Authentication**
- HTTP Basic Auth required for CRUD operations (POST, PUT, DELETE).
- Configure credentials via environment variables:
  - `AUTH_USERNAME` (default: `admin`)
  - `AUTH_PASSWORD` (default: `changeme`)
- All GET endpoints are public (no auth required).
- Example with curl: `curl -u admin:changeme -X POST 'http://localhost:8000/servers' ...`

**Endpoints**
- **POST /servers**: Create a server.
  - Body: `ServerCreate` JSON. Required: `type` (`http|nginx|squid|proxy`), `host`. Optional: `name`, `port`, `scheme` (`http|https`), `path`, `interval` (seconds).
  - Returns: created server (fields: `id`, `name`, `type`, `host`, `port`, `scheme`, `path`, `interval`).

- **GET /servers**: List all servers.

- **GET /servers/{server_id}**: Get server by id.

- **PUT /servers/{server_id}**: Update server (partial). Send only the fields to change. Updating restarts that server's checker task.

- **DELETE /servers/{server_id}**: Delete server and its ping history. If last server is deleted, background checker tasks are disabled.

- **GET /squid**: List only servers with `type == 'squid'`.

- **GET /http**: List servers with `type == 'http'` or `type == 'nginx'`.

- **GET /servers/{server_id}/data**: Returns `server`, `latest` ping, and `history` (last 100 pings) for any server (squid or http/nginx).

- **GET /servers/{server_id}/status**: Lightweight status for the status page and debugging:
  - `server`: server record
  - `task_running`: whether a checker task is active for this server
  - `last_check_ts`: timestamp of last check
  - `uptime_pct`: uptime percentage based on last 5 pings
  - `last_5_pings`: last 5 pings in chronological order

**Models (summary)**
- `ServerCreate`: {name?, type, host, port?, scheme? (http|https), path?, interval?}
- `ServerUpdate`: partial fields (all optional)
- `ServerOut`: persisted server representation (includes `id`)
- `Ping` rows in DB: {id, server_id, ts, ok, status_code, latency_ms, error, headers}

**Examples**
- Create HTTP server:
```
curl -u admin:changeme -X POST 'http://127.0.0.1:8000/servers' -H 'Content-Type: application/json' \
  -d '{"name":"web1","type":"http","host":"example.com","port":80,"path":"/","interval":30}'
```

- Create Squid proxy (uses `SQUID_HTTP_TARGET` by default):
```
curl -u admin:changeme -X POST 'http://127.0.0.1:8000/servers' -H 'Content-Type: application/json' \
  -d '{"name":"squid1","type":"squid","host":"10.0.0.5","port":3128,"interval":60}'
```

- Update interval only:
```
curl -u admin:changeme -X PUT 'http://127.0.0.1:8000/servers/1' -H 'Content-Type: application/json' -d '{"interval":10}'
```

- Read server data (no auth required):
```
curl 'http://127.0.0.1:8000/servers/1/data'
```

**Run locally**
```
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export AUTH_USERNAME='admin'              # optional (default: admin)
export AUTH_PASSWORD='changeme'           # optional (default: changeme)
export SQUID_HTTP_TARGET='https://httpbin.org/get'   # optional override
uvicorn backend.app:app --reload --port 8000
```

**Notes & Extensibility**
- The app exposes the OpenAPI spec at `GET /openapi.json` and interactive docs at `/docs` and `/redoc` (FastAPI built-ins).
- Consider adding authentication, pagination for lists, aggregated `/status/summary` endpoint, or Prometheus `/metrics` for monitoring.