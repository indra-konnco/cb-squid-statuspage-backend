from typing import Optional, Dict, Any, List
import logging
import sys
import os
import base64

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, Depends, Header

from backend.checker import check
from backend import db
from backend import models

import asyncio

# Configure logging to STDOUT
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Proxy & HTTP checker", version="0.2")

# Read credentials from environment variables
AUTH_USERNAME = os.getenv('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', 'changeme')

# in-memory map of running check tasks: server_id -> asyncio.Task
_tasks: Dict[int, asyncio.Task] = {}


# Auth dependency for CRUD operations
async def verify_auth(authorization: Optional[str] = Header(None)) -> bool:
    """Verify HTTP Basic Auth credentials from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail='Missing authorization header')
    
    if not authorization.startswith('Basic '):
        raise HTTPException(status_code=401, detail='Invalid authorization scheme')
    
    try:
        encoded = authorization[6:]  # Remove 'Basic ' prefix
        decoded = base64.b64decode(encoded).decode('utf-8')
        username, password = decoded.split(':', 1)
        
        if username == AUTH_USERNAME and password == AUTH_PASSWORD:
            return True
        else:
            raise HTTPException(status_code=401, detail='Invalid credentials')
    except Exception as e:
        raise HTTPException(status_code=401, detail='Invalid credentials')


async def _check_loop(server: Dict[str, Any]):
    server_id = server['id']
    interval = int(server.get('interval', 60)) or 60
    logger.info(f"Check loop started for server {server_id} ({server.get('name', 'unnamed')}) with interval {interval}s")
    while True:
        # fetch latest server row (in case it was updated)
        s = await db.get_server(server_id)
        if not s:
            logger.info(f"Check loop ended for server {server_id}: server deleted")
            break
        try:
            if s['type'] in ('squid', 'proxy'):
                logger.debug(f"Checking squid proxy {server_id}: {s['host']}:{s['port']}")
                res = await check('squid', s['host'], s['port'], timeout=8.0, test_url=s.get('test_url'))
            else:
                logger.debug(f"Checking http server {server_id}: {s['host']}:{s['port']}{s.get('path', '/')}")
                res = await check('http', s['host'], s['port'], scheme=s.get('scheme') or 'http', path=s.get('path') or '/', timeout=8.0)
            # attach timestamp
            res['ts'] = asyncio.get_event_loop().time()
            await db.add_ping(server_id, res)
            status = "ok" if res.get('ok') else f"failed: {res.get('error', 'unknown')}"
            latency = res.get('latency_ms', 'N/A')
            logger.info(f"Check result for server {server_id}: {status} (latency: {latency}ms)")
        except Exception as e:
            logger.error(f"Exception during check for server {server_id}: {e}", exc_info=True)
            await db.add_ping(server_id, {'ts': asyncio.get_event_loop().time(), 'ok': False, 'error': str(e)})
        # determine current interval (in case updated)
        s2 = await db.get_server(server_id)
        if not s2:
            logger.info(f"Check loop ended for server {server_id}: server deleted during loop")
            break
        interval = int(s2.get('interval') or 60)
        await asyncio.sleep(max(1, interval))


def _start_task_for_server(server: Dict[str, Any]):
    sid = server['id']
    if sid in _tasks and not _tasks[sid].done():
        logger.info(f"Cancelling existing check task for server {sid}")
        _tasks[sid].cancel()
    logger.info(f"Starting check task for server {sid} ({server.get('name', 'unnamed')})")
    _tasks[sid] = asyncio.create_task(_check_loop(server))


def _cancel_task(server_id: int):
    t = _tasks.pop(server_id, None)
    if t and not t.done():
        t.cancel()


@app.on_event('startup')
async def startup():
    logger.info("App startup: initializing database")
    await db.init_db()
    servers = await db.list_servers()
    if not servers:
        logger.info('No servers registered; checker jobs disabled')
        return
    logger.info(f"Found {len(servers)} servers; starting check tasks")
    for s in servers:
        _start_task_for_server(s)


@app.on_event('shutdown')
async def shutdown():
    logger.info("App shutdown: cancelling all check tasks")
    for t in list(_tasks.values()):
        if not t.done():
            t.cancel()
    logger.info("All check tasks cancelled")


@app.post('/servers', response_model=models.ServerOut)
async def create_server(payload: models.ServerCreate, _: bool = Depends(verify_auth)):
    data = payload.dict()
    logger.info(f"Creating server: {data}")
    row = await db.create_server(data)
    _start_task_for_server(row)
    logger.info(f"Server created with id {row['id']}")
    return row


@app.get('/servers', response_model=List[models.ServerOut])
async def list_all_servers():
    return await db.list_servers()


@app.get('/servers/{server_id}', response_model=models.ServerOut)
async def get_server(server_id: int):
    row = await db.get_server(server_id)
    if not row:
        raise HTTPException(status_code=404, detail='server not found')
    return row


@app.put('/servers/{server_id}', response_model=models.ServerOut)
async def update_server(server_id: int, payload: models.ServerUpdate, _: bool = Depends(verify_auth)):
    logger.info(f"Updating server {server_id}: {payload.dict(exclude_unset=True)}")
    row = await db.update_server(server_id, payload.dict(exclude_unset=True))
    if not row:
        logger.warning(f"Server {server_id} not found for update")
        raise HTTPException(status_code=404, detail='server not found')
    _start_task_for_server(row)
    logger.info(f"Server {server_id} updated and task restarted")
    return row


@app.delete('/servers/{server_id}')
async def delete_server(server_id: int, _: bool = Depends(verify_auth)):
    logger.info(f"Deleting server {server_id}")
    _cancel_task(server_id)
    await db.delete_server(server_id)
    # If there are no servers left, cancel any remaining tasks and ensure the checker is disabled
    remaining = await db.list_servers()
    if not remaining:
        logger.info('No servers left after delete; cancelling all checker tasks')
        for sid in list(_tasks.keys()):
            _cancel_task(sid)
        _tasks.clear()
    logger.info(f"Server {server_id} deleted")
    return {'ok': True}


@app.get('/squid')
async def list_squid():
    return await db.list_servers_by_type('squid')


@app.get('/http')
async def list_http():
    # allow both 'http' and 'nginx'
    all = await db.list_servers()
    return [s for s in all if s['type'] in ('http', 'nginx')]


@app.get('/servers/{server_id}/data')
async def server_data(server_id: int):
    s = await db.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail='server not found')
    latest = await db.get_latest_ping(server_id)
    hist = await db.get_pings(server_id, limit=100)
    return {'server': s, 'latest': latest, 'history': hist}


@app.get('/servers/{server_id}/status')
async def server_status(server_id: int):
    """
    Get server status: last 5 pings, uptime %, last check time, and task state.
    Useful for monitoring the checker job activity.
    """
    s = await db.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail='server not found')
    
    # Get last 5 pings
    pings = await db.get_pings(server_id, limit=5)
    pings = list(reversed(pings))  # reverse to chronological order (oldest first)
    
    # Calculate uptime %
    if pings:
        ok_count = sum(1 for p in pings if p['ok'])
        uptime_pct = round((ok_count / len(pings)) * 100, 1)
    else:
        uptime_pct = None
    
    # Get last check time
    latest = await db.get_latest_ping(server_id)
    last_check_ts = latest['ts'] if latest else None
    
    # Check if task is running
    task_running = server_id in _tasks and not _tasks[server_id].done()
    
    return {
        'server': s,
        'task_running': task_running,
        'last_check_ts': last_check_ts,
        'uptime_pct': uptime_pct,
        'last_5_pings': pings,
    }
