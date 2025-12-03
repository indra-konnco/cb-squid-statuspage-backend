#!/bin/bash

##############################################################################
# Bulk Add Servers Script
# 
# This script reads a list of hostnames/IP addresses from a file and bulk-adds
# them as HTTP servers or Squid proxies via the backend API.
#
# Prerequisites:
#   - User must be already registered with the application
#   - Provide valid username and password to login
#
# Server Type Configurations:
#   HTTP: 
#     - Port: 443 (HTTPS)
#     - Path: /api/callback-wormhole
#     - Scheme: https
#   Squid:
#     - Port: 3128
#     - No path or scheme
#
# Usage:
#   ./bulk-add-servers.sh [server_type] [input_file] [api_url] [username] [password]
#
# Examples:
#   ./bulk-add-servers.sh http http-list.txt http://localhost:8000 operator securepass
#   ./bulk-add-servers.sh squid squid-list.txt http://localhost:8000 operator securepass
#
##############################################################################

set -e

# Parse arguments
SERVER_TYPE="${1:-http}"
INPUT_FILE="${2:-bulk-list-cb.txt}"
API_URL="${3:-http://localhost:8000}"
API_USERNAME="${4:-operator}"
API_PASSWORD="${5:-securepass}"

# Validate server type
if [[ ! "$SERVER_TYPE" =~ ^(http|squid)$ ]]; then
    echo "Error: Invalid server type '$SERVER_TYPE'. Must be 'http' or 'squid'."
    exit 1
fi

# Server-specific configuration
if [ "$SERVER_TYPE" = "http" ]; then
    PORT="443"
    API_PATH="/api/callback-wormhole"
    SCHEME="https"
    INTERVAL="30"
else  # squid
    PORT="3128"
    API_PATH=""
    SCHEME=""
    INTERVAL="60"
fi

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}=== Bulk Add $SERVER_TYPE Servers ===${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    print_error "Input file '$INPUT_FILE' not found!"
    exit 1
fi

print_header
print_info "Server Type: $SERVER_TYPE"
print_info "API URL: $API_URL"
print_info "Username: $API_USERNAME"
print_info "Input file: $INPUT_FILE"

if [ "$SERVER_TYPE" = "http" ]; then
    print_info "Server configuration: port=$PORT, path=$API_PATH, interval=$INTERVAL seconds, scheme=$SCHEME"
else
    print_info "Server configuration: port=$PORT, interval=$INTERVAL seconds"
fi
echo ""

# Step 1: Login to get access token
print_info "Step 1: Logging in as '$API_USERNAME'..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$API_USERNAME&password=$API_PASSWORD")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    print_error "Failed to obtain access token"
    print_error "Response: $LOGIN_RESPONSE"
    print_error "Make sure you are using valid username and password."
    exit 1
fi

print_success "Login successful, obtained access token"
echo ""

# Step 2: Bulk add servers
print_info "Step 2: Adding servers from $INPUT_FILE..."
TOTAL_LINES=$(wc -l < "$INPUT_FILE")
SUCCESS_COUNT=0
FAILURE_COUNT=0
SKIP_COUNT=0

while IFS= read -r entry || [ -n "$entry" ]; do
    # Skip empty lines and comments
    if [ -z "$entry" ] || [[ "$entry" =~ ^# ]]; then
        SKIP_COUNT=$((SKIP_COUNT + 1))
        continue
    fi
    
    # Trim whitespace
    entry=$(echo "$entry" | xargs)
    
    # Parse entry based on server type
    if [ "$SERVER_TYPE" = "http" ]; then
        # HTTP: format is "server_name hostname" (space-separated)
        if [[ "$entry" == *" "* ]]; then
            # Has space-separated format: name and hostname
            SERVER_NAME=$(echo "$entry" | cut -d' ' -f1)
            HOST=$(echo "$entry" | cut -d' ' -f2-)
        else
            # Simple format: just hostname, use as both name and host
            SERVER_NAME="$entry"
            HOST="$entry"
        fi
        PARSED_PORT=$PORT
    else
        # Squid: format is "server_name ip_address:port"
        # Split by space (not tab)
        if [[ "$entry" == *" "* ]]; then
            # Has space-separated format: name and ip:port
            SERVER_NAME=$(echo "$entry" | cut -d' ' -f1)
            IP_AND_PORT=$(echo "$entry" | cut -d' ' -f2)
            
            # Split ip_and_port by colon to get ip and port
            if [[ "$IP_AND_PORT" == *:* ]]; then
                HOST="${IP_AND_PORT%:*}"
                PARSED_PORT="${IP_AND_PORT#*:}"
            else
                # No port specified, use default
                HOST="$IP_AND_PORT"
                PARSED_PORT=$PORT
            fi
        else
            # Simple format: just ip address
            SERVER_NAME="$entry"
            HOST="$entry"
            PARSED_PORT=$PORT
        fi
    fi
    
    # Create server payload based on type
    if [ "$SERVER_TYPE" = "http" ]; then
        # HTTP server payload with scheme and path
        PAYLOAD="{\"name\":\"$SERVER_NAME\",\"type\":\"http\",\"host\":\"$HOST\",\"port\":$PARSED_PORT,\"scheme\":\"$SCHEME\",\"path\":\"$API_PATH\",\"interval\":$INTERVAL}"
    else
        # Squid proxy payload (no scheme or path)
        PAYLOAD="{\"name\":\"$SERVER_NAME\",\"type\":\"squid\",\"host\":\"$HOST\",\"port\":$PARSED_PORT,\"interval\":$INTERVAL}"
    fi
    
    # Add server via API
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/servers" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    # Extract HTTP code and response body more reliably
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        SERVER_ID=$(echo "$RESPONSE_BODY" | grep -o '"id":[0-9]*' | cut -d':' -f2)
        print_success "Added '$SERVER_NAME' as $HOST:$PARSED_PORT (Server ID: $SERVER_ID)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        print_error "Failed to add '$SERVER_NAME' as $HOST:$PARSED_PORT (HTTP $HTTP_CODE)"
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
    fi
done < "$INPUT_FILE"

echo ""
print_info "Bulk add operation completed!"
echo -e "${GREEN}Success: $SUCCESS_COUNT${NC}"
echo -e "${RED}Failed: $FAILURE_COUNT${NC}"
echo -e "${YELLOW}Skipped: $SKIP_COUNT${NC}"
echo ""
print_success "Script completed successfully!"

