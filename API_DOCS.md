**API Overview**
- **Service:** Proxy & HTTP checker (FastAPI)
- **Interactive docs:** `GET /docs` (Swagger UI), `GET /redoc` (ReDoc)
- **OpenAPI JSON:** `GET /openapi.json`

**How it works**
- Register servers (Squid proxies or HTTP/nginx) via CRUD endpoints. The service starts a background checker task per server which runs at the server's `interval` and stores the last 100 pings in a SQLite DB (`backend/data.db`).
- Squid check target is configured through the environment variable `SQUID_HTTP_TARGET` (default `https://httpbin.org/get`).

**Authentication**
- **User Registration (POST /auth/register)**: Protected with HTTP Basic Auth using root credentials.
  - Credentials from environment variables:
    - `AUTH_ROOT_USERNAME` (default: `admin`)
    - `AUTH_ROOT_PASSWORD` (default: `changeme`)
  - Example: `curl -u admin:changeme -X POST 'http://localhost:8000/auth/register' ...`
- **User Login (POST /auth/login)**: Public endpoint to obtain JWT access token.
- **CRUD Operations (POST/PUT/DELETE /servers)**: Require valid JWT access token in `Authorization: Bearer <token>` header.
- **Read Operations (GET)**: Public endpoints, no authentication required.

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

- **GET /servers/{server_id}/status**: Returns complete server status and history:
  - `server`: server record
  - `latest`: most recent ping result
  - `history`: last 100 pings in reverse chronological order
  - `task_running`: whether a checker task is active for this server

**Models (summary)**
- `ServerCreate`: {name?, type, host, port?, scheme? (http|https), path?, interval?}
- `ServerUpdate`: partial fields (all optional)
- `ServerOut`: persisted server representation (includes `id`)
- `Ping` rows in DB: {id, server_id, ts, ok, status_code, latency_ms, error, headers}

**Examples**
- Register a new user (requires root credentials):
```
curl -u admin:changeme -X POST 'http://127.0.0.1:8000/auth/register' -H 'Content-Type: application/json' \
  -d '{"username":"operator","password":"securepass"}'
```

- Login to get JWT token:
```
curl -X POST 'http://127.0.0.1:8000/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=operator&password=securepass'
```

- Create HTTP server (requires JWT token):
```
TOKEN="eyJhbGci..."
curl -X POST 'http://127.0.0.1:8000/servers' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"web1","type":"http","host":"example.com","port":80,"path":"/","interval":30}'
```

- Create Squid proxy (uses `SQUID_HTTP_TARGET` by default):
```
TOKEN="eyJhbGci..."
curl -X POST 'http://127.0.0.1:8000/servers' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"squid1","type":"squid","host":"10.0.0.5","port":3128,"interval":60}'
```

- Update interval only:
```
TOKEN="eyJhbGci..."
curl -X PUT 'http://127.0.0.1:8000/servers/1' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"interval":10}'
```

- Read server status and history (no auth required):
```
curl 'http://127.0.0.1:8000/servers/1/status'
```

**Run locally**
```
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option 1: Use .env file (recommended for local development)
cp .env.example .env
# Edit .env with your desired values
uvicorn backend.app:app --reload --port 8000

# Option 2: Set environment variables directly
export AUTH_ROOT_USERNAME='admin'            # optional (default: admin)
export AUTH_ROOT_PASSWORD='changeme'         # optional (default: changeme)
export SQUID_HTTP_TARGET='https://httpbin.org/get'   # optional override
export CORS_ORIGINS='*'                     # optional (default: *, or comma-separated origins)
uvicorn backend.app:app --reload --port 8000
```

The `.env` file is automatically loaded at startup if it exists in the project root.

**Notes & Extensibility**
- The app exposes the OpenAPI spec at `GET /openapi.json` and interactive docs at `/docs` and `/redoc` (FastAPI built-ins).
- Consider adding authentication, pagination for lists, aggregated `/status/summary` endpoint, or Prometheus `/metrics` for monitoring.