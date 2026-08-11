
import aiosqlite
from datetime import datetime, timezone

DB_PATH = "bot.db"

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT NOT NULL,
            is_banned INTEGER NOT NULL DEFAULT 0,
            ban_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            data_json TEXT NOT NULL,
            photo_file_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            processed_at TEXT,
            processed_by INTEGER,
            rejection_reason TEXT,
            claimed_by INTEGER,
            claimed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS application_admin_messages (
            application_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            PRIMARY KEY(application_id, admin_id)
        );
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticket_type TEXT NOT NULL,
            text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            closed_at TEXT,
            closed_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            text TEXT,
            photo_file_id TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id INTEGER PRIMARY KEY,
            reason TEXT NOT NULL,
            banned_by INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        # Migrations for old databases.
        cols = {r[1] for r in await (await db.execute("PRAGMA table_info(applications)")).fetchall()}
        for name, typ in [("claimed_by","INTEGER"),("claimed_at","TEXT")]:
            if name not in cols:
                await db.execute(f"ALTER TABLE applications ADD COLUMN {name} {typ}")
        # Keep only the newest application per user before enforcing the one-profile rule.
        await db.execute("""
            DELETE FROM applications
            WHERE id NOT IN (SELECT MAX(id) FROM applications GROUP BY user_id)
        """)
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_app_user ON applications(user_id)")
        await db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('application_template',?)", ("",))
        await db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('application_template_photo',?)", ("",))
        await db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('group_link',?)", ("",))
        await db.commit()

async def upsert_user(user):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO users(user_id, username, first_name, created_at)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
        """, (user.id, user.username, user.first_name, now()))
        await db.commit()

async def is_banned(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM blacklist WHERE user_id=?", (user_id,))
        return await cur.fetchone() is not None

async def ban_user(user_id, reason, admin_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO blacklist(user_id,reason,banned_by,created_at) VALUES(?,?,?,?)",
                         (user_id,reason,admin_id,now()))
        await db.execute("UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?", (reason,user_id))
        await db.commit()

async def unban_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blacklist WHERE user_id=?", (user_id,))
        await db.execute("UPDATE users SET is_banned=0, ban_reason=NULL WHERE user_id=?", (user_id,))
        await db.commit()

async def get_blacklist():
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("""
        SELECT b.user_id,b.reason,b.banned_by,b.created_at,u.username,u.first_name
        FROM blacklist b LEFT JOIN users u ON u.user_id=b.user_id ORDER BY b.created_at DESC
        """)).fetchall()

async def get_setting(key, default=""):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT value FROM settings WHERE key=?", (key,))).fetchone()
        return row[0] if row else default

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(key,value))
        await db.commit()

async def get_application(app_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("SELECT * FROM applications WHERE id=?", (app_id,))).fetchone()

async def get_user_application(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("SELECT * FROM applications WHERE user_id=?", (user_id,))).fetchone()

async def create_application(user_id, data_json, photo_file_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT id FROM applications WHERE user_id=?", (user_id,))).fetchone()
        if row:
            await db.execute("""UPDATE applications SET data_json=?,photo_file_id=?,status='pending',
                rejection_reason=NULL,processed_at=NULL,processed_by=NULL,claimed_by=NULL,claimed_at=NULL WHERE user_id=?""",
                             (data_json,photo_file_id,user_id))
            await db.commit()
            return row[0]
        cur = await db.execute("""INSERT INTO applications(user_id,data_json,photo_file_id,status,created_at)
                                  VALUES(?,?,?,'pending',?)""",(user_id,data_json,photo_file_id,now()))
        await db.commit()
        return cur.lastrowid

async def update_application_data(app_id, data_json, photo_file_id=None, status=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if status:
            await db.execute("UPDATE applications SET data_json=?,photo_file_id=?,status=? WHERE id=?",
                             (data_json,photo_file_id,status,app_id))
        else:
            await db.execute("UPDATE applications SET data_json=?,photo_file_id=? WHERE id=?",
                             (data_json,photo_file_id,app_id))
        await db.commit()

async def has_pending_application(user_id):
    row = await get_user_application(user_id)
    return row[0] if row and row[4] == "pending" else None

async def list_applications(status):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("""
        SELECT a.id,a.user_id,a.status,a.created_at,u.username,u.first_name,a.claimed_by
        FROM applications a LEFT JOIN users u ON u.user_id=a.user_id
        WHERE a.status=? ORDER BY a.id DESC LIMIT 100
        """,(status,))).fetchall()

async def update_application(app_id,status,admin_id,reason=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""UPDATE applications SET status=?,processed_at=?,processed_by=?,rejection_reason=?,
                            claimed_by=?,claimed_at=? WHERE id=?""",
                         (status,now(),admin_id,reason,admin_id,now(),app_id))
        await db.commit()

async def claim_application(app_id, admin_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""UPDATE applications SET claimed_by=?,claimed_at=?
                                  WHERE id=? AND status='pending' AND (claimed_by IS NULL OR claimed_by=?)""",
                               (admin_id,now(),app_id,admin_id))
        await db.commit()
        if cur.rowcount:
            return True
        row = await (await db.execute("SELECT claimed_by FROM applications WHERE id=?",(app_id,))).fetchone()
        return bool(row and row[0] == admin_id)

async def app_messages(app_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("SELECT admin_id,message_id FROM application_admin_messages WHERE application_id=?",(app_id,))).fetchall()

async def save_app_message(app_id, admin_id, message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO application_admin_messages VALUES(?,?,?)",(app_id,admin_id,message_id))
        await db.commit()

async def list_tickets(status):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("""
        SELECT t.id,t.user_id,t.ticket_type,t.status,t.created_at,u.username,u.first_name
        FROM tickets t LEFT JOIN users u ON u.user_id=t.user_id
        WHERE t.status=? ORDER BY t.id DESC LIMIT 100
        """,(status,))).fetchall()

async def create_ticket(user_id,ticket_type,text):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("INSERT INTO tickets(user_id,ticket_type,text,status,created_at) VALUES(?,?,?,'pending',?)",
                             (user_id,ticket_type,text,now()))
        await db.commit()
        return cur.lastrowid

async def get_ticket(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("SELECT * FROM tickets WHERE id=?",(ticket_id,))).fetchone()

async def close_ticket(ticket_id,status,admin_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status=?,closed_at=?,closed_by=? WHERE id=?",
                         (status,now(),admin_id,ticket_id))
        await db.commit()

async def add_ticket_message(ticket_id,sender_id,sender_type,text=None,photo_file_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO ticket_messages(ticket_id,sender_id,sender_type,text,photo_file_id,created_at)
                            VALUES(?,?,?,?,?,?)""",(ticket_id,sender_id,sender_type,text,photo_file_id,now()))
        await db.commit()

async def get_ticket_messages(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("SELECT sender_id,sender_type,text,photo_file_id,created_at FROM ticket_messages WHERE ticket_id=? ORDER BY id",(ticket_id,))).fetchall()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("SELECT * FROM users WHERE user_id=?",(user_id,))).fetchone()

async def get_user_applications(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("SELECT id,status,created_at,data_json FROM applications WHERE user_id=?",(user_id,))).fetchall()

async def get_user_tickets(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("SELECT id,ticket_type,status,created_at,text FROM tickets WHERE user_id=? ORDER BY id DESC LIMIT 50",(user_id,))).fetchall()

async def list_users():
    async with aiosqlite.connect(DB_PATH) as db:
        return await (await db.execute("""
        SELECT u.user_id,u.username,u.first_name,u.created_at,u.is_banned,
               a.id,a.status,a.data_json
        FROM users u LEFT JOIN applications a ON a.user_id=u.user_id
        ORDER BY u.created_at DESC LIMIT 500
        """)).fetchall()
