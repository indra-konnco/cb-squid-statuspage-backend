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

The application is configured via environment variables. You can set these in your shell or use a `.env` file (if you add `python-dotenv` support, otherwise export them directly).

| Variable | Default | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | `your-secret-key...` | Secret key for signing JWT tokens. **Change this in production!** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token expiration time in minutes. |
| `SQUID_HTTP_TARGET` | `https://httpbin.org/get` | The target URL used to verify Squid proxy connectivity. The checker attempts to reach this URL *through* the proxy. |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins for CORS. Use `*` for all origins (development) or specify domains like `https://yourdomain.com,https://app.yourdomain.com` (production). |

---

## Running the Application

Start the server using `uvicorn`. This command starts the application on port 8000 with auto-reload enabled (useful for development).

```bash
# Set configuration (optional, defaults used if omitted)
export SECRET_KEY='my-super-secret-key'

# Start the server
uvicorn backend.app:app --reload --port 8000
```

Once running, the API is accessible at `http://127.0.0.1:8000`.

---

## Usage Guide

### Authentication
Management endpoints (`POST`, `PUT`, `DELETE`) require a valid **JWT Access Token**.
1.  **Register** a new user.
2.  **Login** to obtain an access token.
3.  Include the token in the `Authorization` header: `Bearer <token>`.

Read-only endpoints (`GET`) are public and do not require authentication.

### Managing Servers

You can manage servers using `curl`, Postman, or the interactive Swagger UI at `http://127.0.0.1:8000/docs`.

#### 1. Register a User
```bash
curl -X POST 'http://127.0.0.1:8000/auth/register' \
  -H 'Content-Type: application/json' \
  -d '{"username": "admin", "password": "securepassword"}'
```

#### 2. Login to Get Token
```bash
curl -X POST 'http://127.0.0.1:8000/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=securepassword'
```
Response:
```json
{"access_token": "eyJhbGci...", "token_type": "bearer"}
```

#### 3. Register an HTTP Server (Protected)
To monitor a standard web server (requires token):

```bash
TOKEN="your_access_token_here"

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

#### 4. Register a Squid Proxy (Protected)
To monitor a Squid proxy (requires token):

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

## API Documentation

For full details on all available endpoints, schemas, and parameters:

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
