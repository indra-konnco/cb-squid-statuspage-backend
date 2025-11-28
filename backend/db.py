import aiosqlite
import asyncio
import json
import time
from typing import Optional, List, Dict, Any

DB_PATH = 'backend/data.db'


async def init_db(path: str = DB_PATH):
    async with aiosqlite.connect(path) as db:
        await db.execute(
            '''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                scheme TEXT DEFAULT 'http',
                path TEXT,
                interval INTEGER NOT NULL DEFAULT 60,
                created_at REAL,
                updated_at REAL
            )
            '''
        )
        # Add scheme column if it doesn't exist (migration for existing DBs)
        try:
            cur = await db.execute("PRAGMA table_info(servers)")
            rows = await cur.fetchall()
            has_scheme = any(row[1] == 'scheme' for row in rows)
            if not has_scheme:
                await db.execute('ALTER TABLE servers ADD COLUMN scheme TEXT DEFAULT \'http\'')
                await db.commit()
        except Exception:
            pass
        await db.execute(
            '''
            CREATE TABLE IF NOT EXISTS pings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                ts REAL NOT NULL,
                ok INTEGER NOT NULL,
                status_code INTEGER,
                latency_ms REAL,
                error TEXT,
                headers TEXT
            )
            '''
        )
        await db.commit()


async def create_server(data: Dict[str, Any], path: str = DB_PATH) -> Dict[str, Any]:
    now = time.time()
    async with aiosqlite.connect(path) as db:
        cur = await db.execute(
            'INSERT INTO servers (name,type,host,port,scheme,path,interval,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
            (
                data.get('name'),
                data['type'],
                data['host'],
                int(data.get('port') or (3128 if data['type'] == 'squid' else 80)),
                data.get('scheme') or 'http',
                data.get('path'),
                int(data.get('interval') or 60),
                now,
                now,
            ),
        )
        await db.commit()
        rowid = cur.lastrowid
        return await get_server(rowid, path)


async def update_server(server_id: int, data: Dict[str, Any], path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    now = time.time()
    async with aiosqlite.connect(path) as db:
        # Build update
        keys = []
        vals = []
        for k in ('name', 'type', 'host', 'port', 'scheme', 'path', 'interval'):
            if k in data:
                keys.append(f"{k} = ?")
                vals.append(data[k])
        if not keys:
            return await get_server(server_id, path)
        vals.extend([now, server_id])
        sql = f"UPDATE servers SET {', '.join(keys)}, updated_at = ? WHERE id = ?"
        await db.execute(sql, vals)
        await db.commit()
        return await get_server(server_id, path)


async def delete_server(server_id: int, path: str = DB_PATH) -> bool:
    async with aiosqlite.connect(path) as db:
        await db.execute('DELETE FROM servers WHERE id = ?', (server_id,))
        await db.execute('DELETE FROM pings WHERE server_id = ?', (server_id,))
        await db.commit()
        return True


async def get_server(server_id: int, path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute('SELECT * FROM servers WHERE id = ?', (server_id,))
        row = await cur.fetchone()
        if not row:
            return None
        return dict(row)


async def list_servers(path: str = DB_PATH) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute('SELECT * FROM servers ORDER BY id')
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def list_servers_by_type(srv_type: str, path: str = DB_PATH) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute('SELECT * FROM servers WHERE type = ? ORDER BY id', (srv_type,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def add_ping(server_id: int, ping: Dict[str, Any], path: str = DB_PATH):
    """Insert a ping entry and prune history to last 100 pings."""
    ts = ping.get('ts', time.time())
    ok = 1 if ping.get('ok') else 0
    status_code = ping.get('status_code')
    latency_ms = ping.get('latency_ms')
    error = ping.get('error')
    headers = json.dumps(ping.get('headers') or {})
    async with aiosqlite.connect(path) as db:
        await db.execute(
            'INSERT INTO pings (server_id,ts,ok,status_code,latency_ms,error,headers) VALUES (?,?,?,?,?,?,?)',
            (server_id, ts, ok, status_code, latency_ms, error, headers),
        )
        await db.commit()
        # prune older pings, keep last 100
        await db.execute(
            '''
            DELETE FROM pings WHERE id IN (
                SELECT id FROM pings WHERE server_id = ? ORDER BY ts DESC LIMIT -1 OFFSET 100
            )
            ''',
            (server_id,),
        )
        await db.commit()


async def get_pings(server_id: int, limit: int = 100, path: str = DB_PATH) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute('SELECT * FROM pings WHERE server_id = ? ORDER BY ts DESC LIMIT ?', (server_id, limit))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_latest_ping(server_id: int, path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute('SELECT * FROM pings WHERE server_id = ? ORDER BY ts DESC LIMIT 1', (server_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
