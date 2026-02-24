import json
import aiosqlite
from datetime import datetime
from config import DB_NAME


class SimpleDB:

    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    async def init_db(self):
        async with aiosqlite.connect(self.db_name) as db:
            # WAL mode untuk mencegah database locked error saat concurrent access
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice TEXT,
                user_id TEXT,
                items TEXT,
                total_price INTEGER,
                payment_method TEXT,
                timestamp TEXT
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT,
                price INTEGER,
                category TEXT,
                spotlight INTEGER DEFAULT 0
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS blacklist (
                user_id TEXT PRIMARY KEY,
                reason TEXT,
                timestamp TEXT
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS auto_react_all (
                channel_id TEXT PRIMARY KEY,
                emojis TEXT
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS auto_react (
                channel_id TEXT PRIMARY KEY,
                emojis TEXT
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS active_tickets (
                channel_id TEXT PRIMARY KEY,
                user_id TEXT,
                items TEXT,
                total_price INTEGER,
                payment_method TEXT,
                status TEXT DEFAULT 'OPEN',
                created_at TEXT
            )''')
            # Migration: tambah kolom spotlight kalau belum ada
            try:
                await db.execute("ALTER TABLE products ADD COLUMN spotlight INTEGER DEFAULT 0")
            except Exception:
                pass
            await db.commit()
        print("✓ Database siap")

    # ─── Transactions ────────────────────────────────────────────

    async def save_transaction(self, trans_data):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    '''INSERT INTO transactions
                       (invoice, user_id, items, total_price, payment_method, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (
                        trans_data["invoice"],
                        trans_data["user_id"],
                        json.dumps(trans_data["items"]),
                        trans_data["total_price"],
                        trans_data.get("payment_method", ""),
                        datetime.now().isoformat(),
                    ),
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error simpan transaksi: {e}")
            return False

    async def get_user_transactions(self, user_id, limit=5):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    '''SELECT * FROM transactions
                       WHERE user_id = ?
                       ORDER BY timestamp DESC
                       LIMIT ?''',
                    (user_id, limit),
                )
                rows = await cursor.fetchall()
            return [self._parse_transaction(row) for row in rows]
        except Exception as e:
            print(f"❌ Error ambil transaksi: {e}")
            return []

    async def get_all_transactions(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM transactions ORDER BY timestamp DESC"
                )
                rows = await cursor.fetchall()
            return [self._parse_transaction(row) for row in rows]
        except Exception as e:
            print(f"❌ Error ambil semua transaksi: {e}")
            return []

    def _parse_transaction(self, row):
        return {
            "invoice": row["invoice"],
            "user_id": row["user_id"],
            "items": json.loads(row["items"]),
            "total_price": row["total_price"],
            "payment_method": row["payment_method"],
            "timestamp": datetime.fromisoformat(row["timestamp"]),
        }

    # ─── Products ────────────────────────────────────────────────

    async def save_products(self, products):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute("DELETE FROM products")
                for p in products:
                    await db.execute(
                        "INSERT INTO products (id, name, price, category, spotlight) VALUES (?, ?, ?, ?, ?)",
                        (p["id"], p["name"], p["price"], p["category"], p.get("spotlight", 0)),
                    )
                await db.commit()
            print(f"✓ Saved {len(products)} products")
            return True
        except Exception as e:
            print(f"❌ Error saving products: {e}")
            return False

    async def load_products(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM products ORDER BY spotlight DESC, id")
                rows = await cursor.fetchall()
            products = [
                {"id": r["id"], "name": r["name"], "price": r["price"], "category": r["category"], "spotlight": r["spotlight"]}
                for r in rows
            ]
            print(f"✓ Loaded {len(products)} products from database")
            return products
        except Exception as e:
            print(f"❌ Error load products: {e}")
            return []

    async def set_spotlight(self, item_id, value: int):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "UPDATE products SET spotlight = ? WHERE id = ?",
                    (value, item_id),
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error set spotlight: {e}")
            return False

    # ─── Blacklist ───────────────────────────────────────────────

    async def add_blacklist(self, user_id, reason=""):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO blacklist (user_id, reason, timestamp) VALUES (?, ?, ?)",
                    (user_id, reason, datetime.now().isoformat()),
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error blacklist: {e}")
            return False

    async def remove_blacklist(self, user_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error hapus blacklist: {e}")
            return False

    async def is_blacklisted(self, user_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(
                    "SELECT 1 FROM blacklist WHERE user_id = ?", (user_id,)
                )
                return await cursor.fetchone() is not None
        except Exception as e:
            print(f"❌ Error cek blacklist: {e}")
            return False

    async def get_blacklist(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(
                    "SELECT user_id, reason, timestamp FROM blacklist ORDER BY timestamp DESC"
                )
                return await cursor.fetchall()
        except Exception as e:
            print(f"❌ Error ambil blacklist: {e}")
            return []

    # ─── Active Tickets ──────────────────────────────────────────

    async def save_ticket(self, channel_id, user_id, items, total_price):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    '''INSERT OR REPLACE INTO active_tickets
                       (channel_id, user_id, items, total_price, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (
                        channel_id,
                        user_id,
                        json.dumps(items),
                        total_price,
                        "OPEN",
                        datetime.now().isoformat(),
                    ),
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error save ticket: {e}")
            return False

    async def get_active_tickets(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT * FROM active_tickets WHERE status = "OPEN"'
                )
                rows = await cursor.fetchall()
            return {
                row["channel_id"]: {
                    "user_id": row["user_id"],
                    "items": json.loads(row["items"]),
                    "total_price": row["total_price"],
                    "payment_method": row["payment_method"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
                for row in rows
            }
        except Exception as e:
            print(f"❌ Error get active tickets: {e}")
            return {}

    async def update_ticket_status(self, channel_id, status, payment_method=None):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                if payment_method:
                    await db.execute(
                        "UPDATE active_tickets SET status = ?, payment_method = ? WHERE channel_id = ?",
                        (status, payment_method, channel_id),
                    )
                else:
                    await db.execute(
                        "UPDATE active_tickets SET status = ? WHERE channel_id = ?",
                        (status, channel_id),
                    )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error update ticket: {e}")
            return False

    async def update_ticket_items(self, channel_id, items):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "UPDATE active_tickets SET items = ? WHERE channel_id = ?",
                    (json.dumps(items), channel_id),
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error update items: {e}")
            return False

    async def update_ticket_total(self, channel_id, total_price):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "UPDATE active_tickets SET total_price = ? WHERE channel_id = ?",
                    (total_price, channel_id),
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error update total: {e}")
            return False

    async def delete_ticket(self, channel_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "DELETE FROM active_tickets WHERE channel_id = ?", (channel_id,)
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error delete ticket: {e}")
            return False

    # ─── Auto React ──────────────────────────────────────────────

    async def save_auto_react(self, channel_id, emojis):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO auto_react (channel_id, emojis) VALUES (?, ?)",
                    (str(channel_id), json.dumps(emojis)),
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error save auto_react: {e}")
            return False

    async def delete_auto_react(self, channel_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "DELETE FROM auto_react WHERE channel_id = ?", (str(channel_id),)
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error delete auto_react: {e}")
            return False

    async def load_auto_react(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute("SELECT channel_id, emojis FROM auto_react")
                rows = await cursor.fetchall()
            return {int(row[0]): json.loads(row[1]) for row in rows}
        except Exception as e:
            print(f"❌ Error load auto_react: {e}")
            return {}

    async def save_auto_react_all(self, channel_id, emojis):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO auto_react_all (channel_id, emojis) VALUES (?, ?)",
                    (str(channel_id), json.dumps(emojis)),
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error save auto_react_all: {e}")
            return False

    async def delete_auto_react_all(self, channel_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "DELETE FROM auto_react_all WHERE channel_id = ?", (str(channel_id),)
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error delete auto_react_all: {e}")
            return False

    async def load_auto_react_all(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(
                    "SELECT channel_id, emojis FROM auto_react_all"
                )
                rows = await cursor.fetchall()
            return {int(row[0]): json.loads(row[1]) for row in rows}
        except Exception as e:
            print(f"❌ Error load auto_react_all: {e}")
            return {}


class ProductsCache:

    def __init__(self, db: SimpleDB, cache_duration=300):
        self.db = db
        self.data = []
        self.last_update = None
        self.cache_duration = cache_duration

    def is_expired(self):
        if not self.last_update:
            return True
        return (datetime.now() - self.last_update).seconds > self.cache_duration

    async def load_from_db(self):
        self.data = await self.db.load_products()
        self.last_update = datetime.now()
        print(f"✓ Cache refreshed: {len(self.data)} products")
        return self.data

    async def get_products(self, force_refresh=False):
        if force_refresh or self.is_expired():
            return await self.load_from_db()
        return self.data

    async def refresh(self):
        return await self.load_from_db()

    def invalidate(self):
        self.last_update = None
        print("📦 Cache invalidated")
