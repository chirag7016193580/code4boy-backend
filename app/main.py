import hmac

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
from datetime import datetime, timezone

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "https://code4boy-web.vercel.app,https://code4boy-web-git-main-code4boy.vercel.app,https://code4boy-fontend.vercel.app,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Database mode: PostgreSQL if DATABASE_URL is set, else SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

# SQLite path fallback
if not USE_POSTGRES:
    if os.environ.get("VERCEL"):
        DB_PATH = "/tmp/app.db"
    elif os.path.exists("/data"):
        DB_PATH = "/data/app.db"
    else:
        DB_PATH = "app.db"
else:
    DB_PATH = ""


# --- Pydantic Models ---

class UserData(BaseModel):
    uid: str
    name: str
    email: str
    photo: Optional[str] = ""
    joinedAt: Optional[str] = ""
    favorites: Optional[list] = []
    watched: Optional[list] = []
    addedTutorials: Optional[list] = []


class VisitorEvent(BaseModel):
    page: str
    referrer: Optional[str] = ""
    screenWidth: Optional[int] = 0
    screenHeight: Optional[int] = 0
    language: Optional[str] = ""
    platform: Optional[str] = ""
    cookieEnabled: Optional[bool] = True
    online: Optional[bool] = True
    connectionType: Optional[str] = ""
    deviceMemory: Optional[float] = 0
    touchPoints: Optional[int] = 0
    # Client-side detected fields (fallback when server-side detection fails)
    ip: Optional[str] = ""
    city: Optional[str] = ""
    country: Optional[str] = ""
    region: Optional[str] = ""
    timezone: Optional[str] = ""
    isp: Optional[str] = ""
    browser: Optional[str] = ""
    os: Optional[str] = ""
    device_type: Optional[str] = ""
    userAgent: Optional[str] = ""


class DownloadEvent(BaseModel):
    fileName: str
    category: Optional[str] = ""


class SiteSettings(BaseModel):
    key: str
    value: str  # JSON string of the settings data


# --- Database Abstraction Layer ---

async def _get_pg_conn():
    import psycopg
    return await psycopg.AsyncConnection.connect(DATABASE_URL)


async def _get_sqlite_conn():
    import aiosqlite
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def db_execute(query, params=(), query_pg=None, params_pg=None):
    """Execute a write query (INSERT/UPDATE/DELETE)."""
    if USE_POSTGRES:
        q = query_pg or query.replace("?", "%s")
        p = params_pg if params_pg is not None else params
        conn = await _get_pg_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(q, p)
            await conn.commit()
    else:
        db = await _get_sqlite_conn()
        await db.execute(query, params)
        await db.commit()
        await db.close()


async def db_fetch_one(query, params=(), query_pg=None, params_pg=None):
    """Execute a query and return one row as a dict."""
    if USE_POSTGRES:
        q = query_pg or query.replace("?", "%s")
        p = params_pg if params_pg is not None else params
        conn = await _get_pg_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(q, p)
                cols = [desc[0] for desc in cur.description] if cur.description else []
                row = await cur.fetchone()
                return dict(zip(cols, row)) if row else None
    else:
        db = await _get_sqlite_conn()
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        await db.close()
        return dict(row) if row else None


async def db_fetch_all(query, params=(), query_pg=None, params_pg=None):
    """Execute a query and return all rows as list of dicts."""
    if USE_POSTGRES:
        q = query_pg or query.replace("?", "%s")
        p = params_pg if params_pg is not None else params
        conn = await _get_pg_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(q, p)
                cols = [desc[0] for desc in cur.description] if cur.description else []
                rows = await cur.fetchall()
                return [dict(zip(cols, row)) for row in rows]
    else:
        db = await _get_sqlite_conn()
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        await db.close()
        return [dict(row) for row in rows]


async def init_db():
    if USE_POSTGRES:
        conn = await _get_pg_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        uid TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        photo TEXT DEFAULT '',
                        joined_at TEXT DEFAULT '',
                        favorites TEXT DEFAULT '[]',
                        watched TEXT DEFAULT '[]',
                        added_tutorials TEXT DEFAULT '[]',
                        last_login TEXT DEFAULT '',
                        login_count INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT '',
                        updated_at TEXT DEFAULT ''
                    )
                """)
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS visitors (
                        id SERIAL PRIMARY KEY,
                        ip TEXT DEFAULT '',
                        user_agent TEXT DEFAULT '',
                        browser TEXT DEFAULT '',
                        browser_version TEXT DEFAULT '',
                        os TEXT DEFAULT '',
                        os_version TEXT DEFAULT '',
                        device TEXT DEFAULT '',
                        device_brand TEXT DEFAULT '',
                        is_mobile INTEGER DEFAULT 0,
                        is_tablet INTEGER DEFAULT 0,
                        is_pc INTEGER DEFAULT 1,
                        is_bot INTEGER DEFAULT 0,
                        page TEXT DEFAULT '',
                        referrer TEXT DEFAULT '',
                        country TEXT DEFAULT '',
                        city TEXT DEFAULT '',
                        region TEXT DEFAULT '',
                        screen_width INTEGER DEFAULT 0,
                        screen_height INTEGER DEFAULT 0,
                        language TEXT DEFAULT '',
                        platform TEXT DEFAULT '',
                        connection_type TEXT DEFAULT '',
                        device_memory REAL DEFAULT 0,
                        touch_points INTEGER DEFAULT 0,
                        visited_at TEXT DEFAULT ''
                    )
                """)
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS downloads (
                        id SERIAL PRIMARY KEY,
                        ip TEXT DEFAULT '',
                        user_agent TEXT DEFAULT '',
                        file_name TEXT DEFAULT '',
                        category TEXT DEFAULT '',
                        downloaded_at TEXT DEFAULT ''
                    )
                """)
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS site_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT DEFAULT '{}',
                        updated_at TEXT DEFAULT ''
                    )
                """)
            await conn.commit()
    else:
        db = await _get_sqlite_conn()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                photo TEXT DEFAULT '',
                joined_at TEXT DEFAULT '',
                favorites TEXT DEFAULT '[]',
                watched TEXT DEFAULT '[]',
                added_tutorials TEXT DEFAULT '[]',
                last_login TEXT DEFAULT '',
                login_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT DEFAULT '',
                user_agent TEXT DEFAULT '',
                browser TEXT DEFAULT '',
                browser_version TEXT DEFAULT '',
                os TEXT DEFAULT '',
                os_version TEXT DEFAULT '',
                device TEXT DEFAULT '',
                device_brand TEXT DEFAULT '',
                is_mobile INTEGER DEFAULT 0,
                is_tablet INTEGER DEFAULT 0,
                is_pc INTEGER DEFAULT 1,
                is_bot INTEGER DEFAULT 0,
                page TEXT DEFAULT '',
                referrer TEXT DEFAULT '',
                country TEXT DEFAULT '',
                city TEXT DEFAULT '',
                region TEXT DEFAULT '',
                screen_width INTEGER DEFAULT 0,
                screen_height INTEGER DEFAULT 0,
                language TEXT DEFAULT '',
                platform TEXT DEFAULT '',
                connection_type TEXT DEFAULT '',
                device_memory REAL DEFAULT 0,
                touch_points INTEGER DEFAULT 0,
                visited_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT DEFAULT '',
                user_agent TEXT DEFAULT '',
                file_name TEXT DEFAULT '',
                category TEXT DEFAULT '',
                downloaded_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT DEFAULT '{}',
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()
        await db.close()


@app.on_event("startup")
async def startup():
    await init_db()


# --- User Data APIs ---

@app.post("/api/user/sync")
async def sync_user(user: UserData):
    """Save or update user data on the server."""
    now = datetime.now(timezone.utc).isoformat()

    row = await db_fetch_one("SELECT * FROM users WHERE uid = ?", (user.uid,))

    if row:
        existing_favorites = json.loads(row["favorites"]) if row["favorites"] else []
        existing_watched = json.loads(row["watched"]) if row["watched"] else []
        existing_added = json.loads(row["added_tutorials"]) if row["added_tutorials"] else []

        merged_favorites = _merge_lists(existing_favorites, user.favorites or [], "id")
        merged_watched = _merge_lists(existing_watched, user.watched or [], "id")
        merged_added = _merge_lists(existing_added, user.addedTutorials or [], "id")

        login_count = (row["login_count"] or 0) + 1

        await db_execute(
            """UPDATE users SET
                name = ?, email = ?, photo = ?,
                favorites = ?, watched = ?, added_tutorials = ?,
                last_login = ?, login_count = ?, updated_at = ?
            WHERE uid = ?""",
            (user.name, user.email, user.photo or "",
             json.dumps(merged_favorites), json.dumps(merged_watched), json.dumps(merged_added),
             now, login_count, now, user.uid)
        )
    else:
        await db_execute(
            """INSERT INTO users (uid, name, email, photo, joined_at, favorites, watched, added_tutorials, last_login, login_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (user.uid, user.name, user.email, user.photo or "",
             user.joinedAt or now,
             json.dumps(user.favorites or []),
             json.dumps(user.watched or []),
             json.dumps(user.addedTutorials or []),
             now, now, now)
        )

    return {"status": "ok", "message": "User data synced"}


@app.get("/api/user/{uid}")
async def get_user(uid: str):
    """Get user data from the server."""
    row = await db_fetch_one("SELECT * FROM users WHERE uid = ?", (uid,))

    if not row:
        return {"status": "not_found"}

    return {
        "status": "ok",
        "data": {
            "uid": row["uid"],
            "name": row["name"],
            "email": row["email"],
            "photo": row["photo"],
            "joinedAt": row["joined_at"],
            "favorites": json.loads(row["favorites"]) if row["favorites"] else [],
            "watched": json.loads(row["watched"]) if row["watched"] else [],
            "addedTutorials": json.loads(row["added_tutorials"]) if row["added_tutorials"] else [],
            "lastLogin": row["last_login"],
            "loginCount": row["login_count"]
        }
    }


@app.post("/api/user/{uid}/update")
async def update_user_data(uid: str, user: UserData):
    """Update specific user data fields."""
    now = datetime.now(timezone.utc).isoformat()

    await db_execute(
        """UPDATE users SET
            favorites = ?, watched = ?, added_tutorials = ?, updated_at = ?
        WHERE uid = ?""",
        (json.dumps(user.favorites or []),
         json.dumps(user.watched or []),
         json.dumps(user.addedTutorials or []),
         now, uid)
    )
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "database": "postgresql" if USE_POSTGRES else "sqlite"}


# --- Visitor Analytics APIs ---

@app.post("/api/track/visit")
async def track_visit(event: VisitorEvent, request: Request):
    """Track a page visit with device/browser/location info."""
    from user_agents import parse as ua_parse

    # Get real client IP - check multiple headers for proxy/CDN compatibility
    # Priority: x-real-ip (Vercel) > x-vercel-forwarded-for > x-forwarded-for > client host
    ip = (
        request.headers.get("x-real-ip")
        or request.headers.get("x-vercel-forwarded-for")
        or request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else "")
    )
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    # Use client-sent IP as fallback if server-side IP is empty or looks like a private/proxy address
    if (not ip or ip.startswith("127.") or ip.startswith("10.") or ip.startswith("172.") or ip.startswith("192.168.") or ip == "::1") and event.ip:
        ip = event.ip

    user_agent_str = request.headers.get("user-agent", "") or event.userAgent or ""
    ua = ua_parse(user_agent_str)

    # Get geo info - prefer client-sent data (from ipapi.co), fallback to server-side lookup
    country = event.country or ""
    city = event.city or ""
    region = event.region or ""

    if not country and not city and ip:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"http://ip-api.com/json/{ip}?fields=country,city,regionName")
                if resp.status_code == 200:
                    geo = resp.json()
                    country = geo.get("country", "")
                    city = geo.get("city", "")
                    region = geo.get("regionName", "")
        except Exception:
            pass

    # Device detection - use server-side UA parsing, fallback to client-sent values
    browser_family = ua.browser.family if ua.browser.family and ua.browser.family != "Other" else (event.browser or "")
    browser_version = ua.browser.version_string or ""
    os_family = ua.os.family if ua.os.family and ua.os.family != "Other" else (event.os or "")
    os_version = ua.os.version_string or ""
    device_family = ua.device.family or ""
    device_brand = ua.device.brand or ""

    # Determine device type flags - use UA parsing first, client-sent as fallback
    is_mobile = 1 if ua.is_mobile else 0
    is_tablet = 1 if ua.is_tablet else 0
    is_pc = 1 if ua.is_pc else 0
    is_bot = 1 if ua.is_bot else 0

    if not is_mobile and not is_tablet and not is_pc and event.device_type:
        dt = event.device_type.lower()
        if dt == "mobile":
            is_mobile = 1
        elif dt == "tablet":
            is_tablet = 1
        elif dt == "desktop":
            is_pc = 1

    now = datetime.now(timezone.utc).isoformat()

    await db_execute(
        """INSERT INTO visitors (
            ip, user_agent, browser, browser_version, os, os_version,
            device, device_brand, is_mobile, is_tablet, is_pc, is_bot,
            page, referrer, country, city, region,
            screen_width, screen_height, language, platform,
            connection_type, device_memory, touch_points, visited_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ip, user_agent_str,
         browser_family, browser_version,
         os_family, os_version,
         device_family, device_brand,
         is_mobile, is_tablet, is_pc, is_bot,
         event.page, event.referrer or "",
         country, city, region,
         event.screenWidth or 0, event.screenHeight or 0,
         event.language or "", event.platform or "",
         event.connectionType or "", event.deviceMemory or 0,
         event.touchPoints or 0, now)
    )
    return {"status": "ok"}


@app.post("/api/track/download")
async def track_download(event: DownloadEvent, request: Request):
    """Track a file download."""
    ip = (
        request.headers.get("x-real-ip")
        or request.headers.get("x-vercel-forwarded-for")
        or request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else "")
    )
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    user_agent_str = request.headers.get("user-agent", "")

    now = datetime.now(timezone.utc).isoformat()

    await db_execute(
        """INSERT INTO downloads (ip, user_agent, file_name, category, downloaded_at)
        VALUES (?, ?, ?, ?, ?)""",
        (ip, user_agent_str, event.fileName, event.category or "", now)
    )
    return {"status": "ok"}


# --- Admin Auth Helper ---

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")


async def verify_admin(x_admin_key: str = Header(default="")):
    """Verify admin API key from request header."""
    if not ADMIN_API_KEY:
        # If no API key is configured, allow access (dev mode)
        return True
    if not x_admin_key or not hmac.compare_digest(x_admin_key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid admin API key")
    return True


# --- Admin Analytics APIs ---

@app.get("/api/admin/stats")
async def admin_stats(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get overall analytics stats for admin dashboard."""
    total_users = (await db_fetch_one("SELECT COUNT(*) as count FROM users")) or {}
    total_visits = (await db_fetch_one("SELECT COUNT(*) as count FROM visitors")) or {}
    total_downloads = (await db_fetch_one("SELECT COUNT(*) as count FROM downloads")) or {}
    unique_visitors = (await db_fetch_one("SELECT COUNT(DISTINCT ip) as count FROM visitors")) or {}

    today_visits = (await db_fetch_one(
        "SELECT COUNT(*) as count FROM visitors WHERE DATE(visited_at) = DATE('now')",
        query_pg="SELECT COUNT(*) as count FROM visitors WHERE DATE(visited_at) = CURRENT_DATE"
    )) or {}

    return {
        "status": "ok",
        "data": {
            "total_users": total_users.get("count", 0),
            "total_visits": total_visits.get("count", 0),
            "today_visits": today_visits.get("count", 0),
            "total_downloads": total_downloads.get("count", 0),
            "unique_visitors": unique_visitors.get("count", 0)
        }
    }


@app.get("/api/admin/users")
async def admin_users(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get all registered users for admin."""
    rows = await db_fetch_all(
        "SELECT uid, name, email, photo, joined_at, last_login, login_count, created_at FROM users ORDER BY created_at DESC"
    )
    users = []
    for row in rows:
        users.append({
            "uid": row["uid"],
            "name": row["name"],
            "email": row["email"],
            "photo": row["photo"],
            "joined_at": row["joined_at"],
            "last_login": row["last_login"],
            "login_count": row["login_count"],
            "created_at": row["created_at"]
        })
    return {"status": "ok", "data": users}


@app.get("/api/admin/visitors")
async def admin_visitors(limit: int = 100, offset: int = 0, x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get recent visitors with device/location info."""
    rows = await db_fetch_all(
        "SELECT * FROM visitors ORDER BY visited_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    visitors = []
    for row in rows:
        visitors.append({
            "id": row["id"],
            "ip": row["ip"],
            "browser": row["browser"],
            "browser_version": row["browser_version"],
            "os": row["os"],
            "os_version": row["os_version"],
            "device": row["device"],
            "device_type": "Mobile" if row["is_mobile"] else ("Tablet" if row["is_tablet"] else "Desktop"),
            "device_brand": row["device_brand"],
            "is_mobile": bool(row["is_mobile"]),
            "is_tablet": bool(row["is_tablet"]),
            "is_pc": bool(row["is_pc"]),
            "is_bot": bool(row["is_bot"]),
            "page": row["page"],
            "referrer": row["referrer"],
            "country": row["country"],
            "city": row["city"],
            "region": row["region"],
            "screen_width": row["screen_width"],
            "screen_height": row["screen_height"],
            "language": row["language"],
            "platform": row["platform"],
            "connection_type": row["connection_type"],
            "visited_at": row["visited_at"]
        })
    return {"status": "ok", "data": visitors}


@app.get("/api/admin/analytics/browsers")
async def analytics_browsers(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get browser usage breakdown."""
    rows = await db_fetch_all(
        "SELECT browser, COUNT(*) as count FROM visitors WHERE browser != '' GROUP BY browser ORDER BY count DESC LIMIT 10"
    )
    return {"status": "ok", "data": [{"browser": row["browser"], "count": row["count"]} for row in rows]}


@app.get("/api/admin/analytics/os")
async def analytics_os(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get OS usage breakdown."""
    rows = await db_fetch_all(
        "SELECT os, COUNT(*) as count FROM visitors WHERE os != '' GROUP BY os ORDER BY count DESC LIMIT 10"
    )
    return {"status": "ok", "data": [{"os": row["os"], "count": row["count"]} for row in rows]}


@app.get("/api/admin/analytics/countries")
async def analytics_countries(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get country breakdown."""
    rows = await db_fetch_all(
        "SELECT country, COUNT(*) as count FROM visitors WHERE country != '' GROUP BY country ORDER BY count DESC LIMIT 20"
    )
    return {"status": "ok", "data": [{"country": row["country"], "count": row["count"]} for row in rows]}


@app.get("/api/admin/analytics/devices")
async def analytics_devices(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get device type breakdown (mobile/tablet/pc)."""
    mobile = (await db_fetch_one("SELECT COUNT(*) as count FROM visitors WHERE is_mobile = 1")) or {}
    tablet = (await db_fetch_one("SELECT COUNT(*) as count FROM visitors WHERE is_tablet = 1")) or {}
    pc = (await db_fetch_one("SELECT COUNT(*) as count FROM visitors WHERE is_pc = 1")) or {}
    bot = (await db_fetch_one("SELECT COUNT(*) as count FROM visitors WHERE is_bot = 1")) or {}
    return {"status": "ok", "data": [
        {"device_type": "Mobile", "count": mobile.get("count", 0)},
        {"device_type": "Tablet", "count": tablet.get("count", 0)},
        {"device_type": "Desktop", "count": pc.get("count", 0)},
        {"device_type": "Bot", "count": bot.get("count", 0)}
    ]}


@app.get("/api/admin/analytics/pages")
async def analytics_pages(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get most visited pages."""
    rows = await db_fetch_all(
        "SELECT page, COUNT(*) as count FROM visitors WHERE page != '' GROUP BY page ORDER BY count DESC LIMIT 20"
    )
    return {"status": "ok", "data": [{"page": row["page"], "count": row["count"]} for row in rows]}


@app.get("/api/admin/analytics/downloads")
async def analytics_downloads_stats(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get download stats."""
    rows = await db_fetch_all(
        "SELECT file_name, category, COUNT(*) as count FROM downloads GROUP BY file_name ORDER BY count DESC LIMIT 20"
    )
    return {"status": "ok", "data": [{"file_name": row["file_name"], "category": row["category"], "count": row["count"]} for row in rows]}


@app.get("/api/admin/analytics/daily")
async def analytics_daily(x_admin_key: str = Header(default="")):
    await verify_admin(x_admin_key)
    """Get daily visit counts for the last 30 days."""
    rows = await db_fetch_all(
        "SELECT DATE(visited_at) as date, COUNT(*) as count FROM visitors WHERE visited_at >= datetime('now', '-30 days') GROUP BY DATE(visited_at) ORDER BY date ASC",
        query_pg="SELECT DATE(visited_at) as date, COUNT(*) as count FROM visitors WHERE visited_at::timestamp >= NOW() - INTERVAL '30 days' GROUP BY DATE(visited_at) ORDER BY date ASC"
    )
    return {"status": "ok", "data": [{"date": str(row["date"]), "count": row["count"]} for row in rows]}


# --- Site Settings APIs (Server-side storage for cross-device sync) ---

@app.post("/api/admin/site-settings")
async def save_site_settings(settings: SiteSettings, x_admin_key: str = Header(default="")):
    """Save a site setting to the server (admin only).
    This ensures settings are stored on the server and available to all devices."""
    await verify_admin(x_admin_key)
    now = datetime.now(timezone.utc).isoformat()

    row = await db_fetch_one("SELECT * FROM site_settings WHERE key = ?", (settings.key,))
    if row:
        await db_execute(
            "UPDATE site_settings SET value = ?, updated_at = ? WHERE key = ?",
            (settings.value, now, settings.key)
        )
    else:
        await db_execute(
            "INSERT INTO site_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (settings.key, settings.value, now)
        )
    return {"status": "ok", "message": "Setting saved"}


@app.get("/api/settings/{key}")
async def get_site_setting(key: str):
    """Get a site setting by key (public - no auth required).
    This is called by the frontend on every page load to get the latest settings."""
    row = await db_fetch_one("SELECT value FROM site_settings WHERE key = ?", (key,))
    if not row:
        return {"status": "not_found", "data": None}
    return {"status": "ok", "data": json.loads(row["value"])}


@app.get("/api/settings")
async def get_all_site_settings():
    """Get all site settings (public - no auth required).
    Returns all settings in one call for efficient page loading."""
    rows = await db_fetch_all("SELECT key, value FROM site_settings")
    result = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            result[row["key"]] = row["value"]
    return {"status": "ok", "data": result}


@app.delete("/api/admin/site-settings/{key}")
async def delete_site_setting(key: str, x_admin_key: str = Header(default="")):
    """Delete a site setting (admin only)."""
    await verify_admin(x_admin_key)
    await db_execute("DELETE FROM site_settings WHERE key = ?", (key,))
    return {"status": "ok", "message": "Setting deleted"}


# --- Helper ---

def _merge_lists(server_list: list, client_list: list, key: str) -> list:
    """Merge two lists of dicts by a key, keeping server data and adding new client data."""
    existing_ids = {item.get(key) for item in server_list if isinstance(item, dict)}
    merged = list(server_list)
    for item in client_list:
        if isinstance(item, dict) and item.get(key) not in existing_ids:
            merged.append(item)
            existing_ids.add(item.get(key))
    return merged
