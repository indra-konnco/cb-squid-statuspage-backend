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
| `AUTH_USERNAME` | `admin` | Username for HTTP Basic Auth (required for POST/PUT/DELETE). |
| `AUTH_PASSWORD` | `changeme` | Password for HTTP Basic Auth. **Change this in production!** |
| `SQUID_HTTP_TARGET` | `https://httpbin.org/get` | The target URL used to verify Squid proxy connectivity. The checker attempts to reach this URL *through* the proxy. |

---

## Running the Application

Start the server using `uvicorn`. This command starts the application on port 8000 with auto-reload enabled (useful for development).

```bash
# Set credentials (optional, defaults used if omitted)
export AUTH_USERNAME='myadmin'
export AUTH_PASSWORD='mypassword'

# Start the server
uvicorn backend.app:app --reload --port 8000
```

Once running, the API is accessible at `http://127.0.0.1:8000`.

---

## Usage Guide

### Authentication
Management endpoints (`POST`, `PUT`, `DELETE`) require HTTP Basic Authentication.
-   **User**: Value of `AUTH_USERNAME`
-   **Password**: Value of `AUTH_PASSWORD`

Read-only endpoints (`GET`) are public and do not require authentication.

### Managing Servers

You can manage servers using `curl`, Postman, or the interactive Swagger UI at `http://127.0.0.1:8000/docs`.

#### 1. Register an HTTP Server
To monitor a standard web server:

```bash
curl -u admin:changeme -X POST 'http://127.0.0.1:8000/servers' \
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

#### 2. Register a Squid Proxy
To monitor a Squid proxy. The checker will attempt to connect to `SQUID_HTTP_TARGET` through this proxy.

```bash
curl -u admin:changeme -X POST 'http://127.0.0.1:8000/servers' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Gateway Proxy",
    "type": "squid",
    "host": "10.0.0.5",
    "port": 3128,
    "interval": 60
  }'
```

#### 3. List All Servers
```bash
curl 'http://127.0.0.1:8000/servers'
```

#### 4. View Server Status & History
Get the server details, latest ping status, and the last 100 ping records.
```bash
curl 'http://127.0.0.1:8000/servers/1/data'
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
