# Bulk Add Servers Script

This script automates the bulk addition of HTTP servers and Squid proxies to the proxy & callback status checker backend via the REST API.

## Features

- **Multi-server type support** (HTTP and Squid proxy)
- **Bulk registration** from a hostname/IP list file
- **User login** with JWT token authentication
- **Server-specific configurations** (different ports, paths, intervals per type)
- **Configurable parameters** (server type, input file, API URL, credentials)
- **Color-coded output** for easy monitoring
- **Error handling** with detailed feedback

## Prerequisites

- `bash` shell
- `curl` command-line tool
- Backend API running and accessible
- Registered user account with valid credentials

## Server Type Configurations

### HTTP Servers
- **Port:** 443 (HTTPS)
- **Path:** `/api/callback-wormhole`
- **Scheme:** https
- **Interval:** 30 seconds
- **Input file format:** One domain per line (e.g., `example.com`)

### Squid Proxies
- **Port:** 3128
- **Path:** None
- **Scheme:** None
- **Interval:** 60 seconds
- **Input file format:** One IP address per line (e.g., `192.168.1.1`)

## Usage

### Basic Usage (HTTP with defaults)

```bash
./bulk-add-servers.sh http bulk-list-cb.txt
```

This will:
- Use server type: `http`
- Read from `bulk-list-cb.txt`
- Use `http://localhost:8000` as the API URL
- Use `operator:securepass` as login credentials

### Advanced Usage (all parameters)

```bash
./bulk-add-servers.sh [server_type] [input_file] [api_url] [username] [password]
```

**Parameters:**

| Parameter | Description | Default |
| --- | --- | --- |
| `server_type` | Type of server: `http` or `squid` | `http` |
| `input_file` | Path to list file | `bulk-list-cb.txt` |
| `api_url` | Backend API base URL | `http://localhost:8000` |
| `username` | Username for API authentication | `operator` |
| `password` | Password for API authentication | `securepass` |

### Examples

**Add HTTP servers from custom file:**
```bash
./bulk-add-servers.sh http my-domains.txt http://localhost:8000 operator securepass
```

**Add Squid proxies to remote API:**
```bash
./bulk-add-servers.sh squid proxy-list.txt https://api.example.com:8443 myuser mypass
```

**Add HTTP servers with defaults:**
```bash
./bulk-add-servers.sh http http-domains.txt
```

**Add Squid proxies with custom API URL:**
```bash
./bulk-add-servers.sh squid squid-ips.txt http://api.internal:8000 operator securepass
```

## Input File Format

### HTTP Server List (`http-domains.txt`)

One domain/hostname per line:

```
api.aryagunasatria.com
api.berkahvista.com
api.delapantiang.com
# Comments are supported
api.sonarmatrix.com
```

### Squid Proxy List (`squid-ips.txt`)

**Format:** `{server_name}\t{ip_address}:{port}` (tab-separated)

One Squid proxy per line with name and IP:port:

```
proxy-asia	192.168.1.1:3128
proxy-eu	192.168.1.2:3128
proxy-us	10.0.0.1:3128
# Comments are supported
proxy-backup	172.16.0.5:3128
```

**Supported formats:**
- Full format (recommended): `proxy-name	192.168.1.1:3128`
- Simple format: `192.168.1.1` (uses default port 3128, name is `squid-192.168.1.1`)
- Custom port: Any port can be specified after the colon

**Rules (both file types):**
- One entry per line
- Empty lines are ignored
- Lines starting with `#` are treated as comments and skipped
- Whitespace (spaces/tabs at start/end) is trimmed automatically
- For Squid, use tab character to separate server name from IP:port

## How It Works

### Step 1: Validate Server Type
- Checks if server type is either `http` or `squid`
- Exits with error if invalid

### Step 2: Apply Server-Specific Configuration
- Sets appropriate port, path, scheme, and interval based on server type

### Step 3: Login
- Logs in with provided username/password to obtain a JWT access token
- Token is used for all subsequent API calls (server creation)

### Step 4: Bulk Add Servers
- Iterates through each entry in the input file
- **For HTTP servers:** Each line is a domain/hostname
  - Creates server with that hostname
  - Generates name: `http-{hostname}`
- **For Squid proxies:** Each line can be in two formats:
  - Tab-separated: `{server_name}\t{ip}:{port}` → uses provided name and IP:port
  - Simple: `{ip}` or `{ip}:{port}` → generates name as `squid-{ip}`, uses provided/default port
- Logs success/failure for each server
- Reports summary statistics

## Output

The script provides color-coded output for easy monitoring:

```
=== Bulk Add http Servers ===
[INFO] Server Type: http
[INFO] API URL: http://localhost:8000
[INFO] Username: operator
[INFO] Input file: bulk-list-cb.txt
[INFO] Server configuration: port=443, path=/api/callback-wormhole, interval=30 seconds, scheme=https

[INFO] Step 1: Logging in as 'operator'...
[SUCCESS] Login successful, obtained access token

[INFO] Step 2: Adding servers from bulk-list-cb.txt...
[SUCCESS] Added 'api.aryagunasatria.com' (Server ID: 1)
[SUCCESS] Added 'api.berkahvista.com' (Server ID: 2)
[ERROR] Failed to add 'invalid.domain' (HTTP 400)
...

[INFO] Bulk add operation completed!
Success: 198
Failed: 1
Skipped: 0

[SUCCESS] Script completed successfully!
```

## Error Handling

The script handles various error scenarios:

| Scenario | Action |
| --- | --- |
| Invalid server type | Exit with error message |
| Input file not found | Exit with error message |
| Login fails | Exit with error message and instructions |
| Individual server add fails | Log error and continue to next server |

## Troubleshooting

### "curl: command not found"
Install curl:
```bash
# macOS
brew install curl

# Ubuntu/Debian
sudo apt-get install curl

# CentOS/RHEL
sudo yum install curl
```

### "Failed to obtain access token"
- Verify API is running: `curl http://localhost:8000/docs`
- Check username and password are correct
- Verify user account is registered with the backend

### "Permission denied" error when running script
Make the script executable:
```bash
chmod +x bulk-add-servers.sh
```

### "Error: Invalid server type"
Make sure server type is either `http` or `squid`:
```bash
# Correct
./bulk-add-servers.sh http my-list.txt

# Wrong
./bulk-add-servers.sh https my-list.txt  # ✗ https is not valid
./bulk-add-servers.sh proxy my-list.txt  # ✗ proxy is not valid
```

### High failure rate on server additions
- Check entries in the input file are valid (domains or IPs)
- Verify the backend database is accessible
- Check API logs for detailed error messages

## Customization

To modify server configuration, edit the script and change these variables in the configuration section:

```bash
# For HTTP servers
if [ "$SERVER_TYPE" = "http" ]; then
    PORT="443"                          # Change port
    API_PATH="/api/callback-wormhole"   # Change path
    SCHEME="https"                      # Change to "http" or "https"
    INTERVAL="30"                       # Change interval (seconds)
else
    # For Squid proxies
    PORT="3128"                         # Change port
    INTERVAL="60"                       # Change interval (seconds)
fi
```

## Tips & Best Practices

1. **Test with a small subset first:**
   ```bash
   head -5 bulk-list-cb.txt > test-list.txt
   ./bulk-add-servers.sh http test-list.txt
   ```

2. **Monitor the API during bulk add:**
   ```bash
   # In another terminal:
   tail -f /var/log/app.log
   ```

3. **Verify servers were added:**
   ```bash
   # List all servers
   curl http://localhost:8000/servers
   
   # List only HTTP servers
   curl http://localhost:8000/http
   
   # List only Squid proxies
   curl http://localhost:8000/squid
   ```

4. **Use environment variables for credentials:**
   ```bash
   export API_USERNAME="operator"
   export API_PASSWORD="securepass"
   ./bulk-add-servers.sh http list.txt http://localhost:8000 "$API_USERNAME" "$API_PASSWORD"
   ```

5. **Create separate lists for each server type:**
   ```bash
   # http-list.txt
   api.example.com
   webhook.example.com
   
   # squid-list.txt
   192.168.1.1
   10.0.0.5
   ```

## Security Notes

- **Never commit credentials** to version control
- Use environment variables for sensitive data in CI/CD
- Use `.env` file (git-ignored) for local development
- In production, use proper secret management (HashiCorp Vault, AWS Secrets Manager, etc.)
- Ensure user credentials are not exposed in shell history: `HISTCONTROL=ignorespace ./bulk-add-servers.sh ...`

## License

This script is part of the Proxy & Callback Status Page project.


