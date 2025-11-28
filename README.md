# nginx-cb-squid-status-page — backend checker

This repository contains a small FastAPI backend that can check Squid proxy servers and generic HTTP servers (e.g. nginx).

**Features:**
- CRUD endpoints to register and manage servers
- Per-server background checker tasks that run at configurable intervals
- HTTP Basic Auth protection for CRUD operations (create/update/delete)
- Ping history stored in SQLite (last 100 pings per server)
- Public read endpoints for monitoring (list, get, data, status)

Quick start (recommended in a virtualenv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Optional: set credentials (default: admin / changeme)
export AUTH_USERNAME='admin'
export AUTH_PASSWORD='changeme'
export SQUID_HTTP_TARGET='https://httpbin.org/get'

uvicorn backend.app:app --reload --port 8000
```

**API Overview:**

All GET endpoints are public. POST/PUT/DELETE endpoints require HTTP Basic Auth:

```bash
# Create HTTP server (requires auth)
curl -u admin:changeme -X POST 'http://127.0.0.1:8000/servers' -H 'Content-Type: application/json' \
  -d '{"name":"web1","type":"http","host":"example.com","port":80,"path":"/","interval":30}'

# List servers (public)
curl 'http://127.0.0.1:8000/servers'

# Get server data (public)
curl 'http://127.0.0.1:8000/servers/1/data'
```

See `API_DOCS.md` for full endpoint documentation.

Unit tests:

```bash
pip install -r backend/requirements.txt
pytest -q
```

**Static status page:**

A small example static status page is in `static/status.html` that polls the API and displays per-server status:

```bash
python -m http.server 8080
# then open http://localhost:8080/static/status.html in your browser
```

**Postman collection:**

Import `postman_collection.json` into Postman to get example requests. The collection includes variables for `baseUrl`, `authUser`, and `authPass` for easy configuration.
