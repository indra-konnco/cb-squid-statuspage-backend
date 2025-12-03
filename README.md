# Proxy & Callback Status Page — Backend Checker

This repository contains a lightweight, asynchronous FastAPI backend designed to monitor the health and status of Squid proxy servers and generic HTTP servers (e.g., Nginx, Apache). It performs periodic checks and provides a REST API to manage monitored servers and retrieve their status history.

## Features

-   **Multi-Protocol Support**: Native support for checking:
    -   **Squid Proxies**: Verifies proxy connectivity by tunneling requests.
    -   **HTTP/HTTPS Servers**: Checks standard web servers for reachability and status codes.
-   **Background Monitoring**: Runs asynchronous background tasks for each registered server to perform periodic health checks.
-   **Configurable Intervals**: Set custom check intervals (in seconds) per server.
-   **Persistence**: Stores server configurations and the last 100 ping results in a local SQLite database (`backend/data.db`).
-   **Secure Management**: Protects Create, Update, and Delete (CRUD) operations with HTTP Basic Authentication.
-   **Public Monitoring**: Exposes read-only endpoints for status dashboards without authentication.
-   **Swagger UI**: Built-in interactive API documentation.

---

## Installation

Prerequisites: Python 3.8+

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd nginx-cb-squid-status-page
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r backend/requirements.txt
    ```

---

## Configuration

The application is configured via environment variables. You can set these in your shell or use a `.env` file for convenience during local development.

### Using a `.env` File (Recommended for Development)

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your desired configuration:
   ```
   AUTH_USERNAME=admin
   AUTH_PASSWORD=changeme
   SQUID_HTTP_TARGET=https://httpbin.org/get
   ```

3. Start the application — the `.env` file is automatically loaded:
   ```bash
   uvicorn backend.app:app --reload --port 8000
   ```

### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `AUTH_ROOT_USERNAME` | `admin` | Username for root user registration (HTTP Basic Auth). |
| `AUTH_ROOT_PASSWORD` | `changeme` | Password for root user registration (HTTP Basic Auth). |
| `SQUID_HTTP_TARGET` | `https://httpbin.org/get` | The target URL used to verify Squid proxy connectivity. The checker attempts to reach this URL *through* the proxy. |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins for CORS. Use `*` for all origins (development) or specify domains like `https://yourdomain.com,https://app.yourdomain.com` (production). |

---

## Running the Application

Start the server using `uvicorn`. This command starts the application on port 8000 with auto-reload enabled (useful for development).

```bash
# If using .env file (recommended)
uvicorn backend.app:app --reload --port 8000

# Or set variables directly in the shell
export AUTH_USERNAME='admin'
export AUTH_PASSWORD='changeme'
uvicorn backend.app:app --reload --port 8000
```

Once running, the API is accessible at `http://127.0.0.1:8000`.

---

## Usage Guide

### Authentication

The application uses a **two-tier authentication system**:

1. **Root User Registration** (HTTP Basic Auth):
   - Protect user registration with root credentials (`AUTH_ROOT_USERNAME` / `AUTH_ROOT_PASSWORD`).
   - Only the root user can register new application users.
   - Once users are registered, they can login to receive JWT tokens.

2. **User Login & CRUD Operations** (JWT):
   - Regular users register their credentials (HTTP Basic Auth protected).
   - Users login to receive JWT access tokens.
   - JWT tokens are used to perform CRUD operations (create/update/delete servers).
   - Tokens expire after 30 minutes.

3. **Public Read Operations**:
   - All GET endpoints are public (no authentication required).

### Managing Servers

You can manage servers using `curl`, Postman, or the interactive Swagger UI at `http://127.0.0.1:8000/docs`.

#### 1. Register a New User (Root Auth Required)
```bash
curl -u admin:changeme -X POST 'http://127.0.0.1:8000/auth/register' \
  -H 'Content-Type: application/json' \
  -d '{"username":"operator","password":"securepass"}'
```

#### 2. Login to Get JWT Token
```bash
curl -X POST 'http://127.0.0.1:8000/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=operator&password=securepass'
```

Response:
```json
{"access_token": "eyJhbGci...", "token_type": "bearer"}
```

#### 3. Create an HTTP Server (JWT Token Required)
```bash
TOKEN="eyJhbGci..."

curl -X POST 'http://127.0.0.1:8000/servers' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Production Web",
    "type": "http",
    "host": "example.com",
    "port": 80,
    "path": "/",
    "interval": 30
  }'
```

#### 4. Create a Squid Proxy Server (JWT Token Required)
```bash
curl -X POST 'http://127.0.0.1:8000/servers' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Gateway Proxy",
    "type": "squid",
    "host": "10.0.0.5",
    "port": 3128,
    "interval": 60
  }'
```

#### 5. List All Servers (Public)
```bash
curl 'http://127.0.0.1:8000/servers'
```

#### 6. View Server Status & History (Public)
Get the server details, latest ping status, and the last 100 ping records.
```bash
curl 'http://127.0.0.1:8000/servers/1/status'
```

---

## Bulk Server Management

### Bulk Add Servers from File

A bash script is provided to bulk-add HTTP servers from a list file (`bulk-list-cb.txt`).

**Quick Start:**

```bash
# 1. Ensure backend is running on port 8000
uvicorn backend.app:app --port 8000 &

# 2. Edit bulk-list-cb.txt with your hostnames (one per line)

# 3. Run the bulk add script
./bulk-add-servers.sh

# Or with custom API endpoint and credentials:
./bulk-add-servers.sh https://api.example.com admin changeme operator securepass
```

**Configuration:**

All servers added via the script are configured with:
- Port: `443` (HTTPS)
- Path: `/api/callback-wormhole`
- Interval: `30` seconds
- Scheme: `https`

**Features:**

- Automatic user registration (register if doesn't exist, login to get JWT token)
- Color-coded output for easy monitoring
- Handles 100+ servers efficiently
- Detailed success/failure reporting

For detailed documentation, see **[BULK_ADD_SCRIPT.md](BULK_ADD_SCRIPT.md)**.

---

## API Documentation

1.  Start the application.
2.  Open **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** in your browser.

See also `API_DOCS.md` in this repository for a static reference.

---

## Static Status Page

A simple HTML/JS status dashboard is included in the `static/` directory. It polls the API and displays the status of all monitored servers.

To run it:

1.  Start the backend API on port 8000 (as described above).
2.  Serve the static directory on a different port (e.g., 8080):
    ```bash
    python -m http.server 8080
    ```
3.  Open `http://localhost:8080/static/status.html` in your browser.

*Note: Ensure the backend allows CORS if you host the static page on a different domain/port in production. For local testing with `localhost`, it typically works out of the box.*

---

## Development & Testing

### Running Tests
The project uses `pytest` for unit testing.

```bash
# Install test dependencies (included in requirements.txt)
pip install -r backend/requirements.txt

# Run tests
pytest -q
```

### Database
The application uses a SQLite database located at `backend/data.db`. This file is automatically created on the first run. To reset the database, simply delete this file and restart the application.
