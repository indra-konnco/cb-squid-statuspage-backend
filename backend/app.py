from typing import Optional, Dict, Any, List
import logging
import sys
import os
import base64

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

from backend.checker import check
from backend import db
from backend import models

import asyncio
import time

# Configure logging to STDOUT
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


app = FastAPI(title="Proxy & HTTP checker", version="0.2")

# Read configuration from environment variables
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Parse CORS origins (comma-separated list or "*" for all)
if CORS_ORIGINS == '*':
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in CORS_ORIGINS.split(',')]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# in-memory map of running check tasks: server_id -> asyncio.Task
_tasks: Dict[int, asyncio.Task] = {}


# Auth functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = models.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await db.get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def _check_loop(server: Dict[str, Any]):
    server_id = server['id']
    interval = int(server.get('interval', 60)) or 60
    logger.info(f"Check loop started for server {server_id} ({server.get('name', 'unnamed')}, type: {server.get('type', 'unknown')}) with interval {interval}s")
    while True:
        # fetch latest server row (in case it was updated)
        s = await db.get_server(server_id)
        if not s:
            logger.info(f"Check loop ended for server {server_id}: server deleted")
            break
        try:
            if s['type'] in ('squid', 'proxy'):
                logger.info(f"Checking server {server_id} (type: squid) - {s['host']}:{s['port']}")
                res = await check('squid', s['host'], s['port'], timeout=8.0, test_url=s.get('test_url'))
            else:
                logger.info(f"Checking server {server_id} (type: {s['type']}) - {s['host']}:{s['port']}{s.get('path', '/')}")
                res = await check('http', s['host'], s['port'], scheme=s.get('scheme') or 'http', path=s.get('path') or '/', timeout=8.0)
            # attach timestamp
            res['ts'] = time.time()
            await db.add_ping(server_id, res)
            status = "ok" if res.get('ok') else f"failed: {res.get('error', 'unknown')}"
            latency = res.get('latency_ms', 'N/A')
            logger.info(f"Check result for server {server_id} (type: {s['type']}): {status} (latency: {latency}ms)")
        except Exception as e:
            logger.error(f"Exception during check for server {server_id} (type: {s.get('type', 'unknown')}): {e}", exc_info=True)
            await db.add_ping(server_id, {'ts': time.time(), 'ok': False, 'error': str(e)})
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


@app.post("/auth/register", response_model=models.User)
async def register(user: models.UserCreate):
    db_user = await db.get_user_by_username(user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    return await db.create_user(user.username, hashed_password)


@app.post("/auth/login", response_model=models.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post('/servers', response_model=models.ServerOut)
async def create_server(payload: models.ServerCreate, current_user: models.User = Depends(get_current_user)):
    data = payload.dict()
    logger.info(f"Creating server: {data} by user {current_user['username']}")
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
async def update_server(server_id: int, payload: models.ServerUpdate, current_user: models.User = Depends(get_current_user)):
    logger.info(f"Updating server {server_id}: {payload.dict(exclude_unset=True)} by user {current_user['username']}")
    row = await db.update_server(server_id, payload.dict(exclude_unset=True))
    if not row:
        logger.warning(f"Server {server_id} not found for update")
        raise HTTPException(status_code=404, detail='server not found')
    _start_task_for_server(row)
    logger.info(f"Server {server_id} updated and task restarted")
    return row


@app.delete('/servers/{server_id}')
async def delete_server(server_id: int, current_user: models.User = Depends(get_current_user)):
    logger.info(f"Deleting server {server_id} by user {current_user['username']}")
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


@app.get('/servers/{server_id}/status')
async def server_status(server_id: int):
    """
    Get server status with full history and monitoring data.
    Returns: server details, latest ping, full history (last 100 pings), and task state.
    """
    s = await db.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail='server not found')
    
    # Get latest ping and full history
    latest = await db.get_latest_ping(server_id)
    history = await db.get_pings(server_id, limit=100)
    
    # Check if task is running
    task_running = server_id in _tasks and not _tasks[server_id].done()
    
    return {
        'server': s,
        'latest': latest,
        'history': history,
        'task_running': task_running,
    }
