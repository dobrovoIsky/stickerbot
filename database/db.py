import aiosqlite
import logging
from config import config

logger = logging.getLogger(__name__)

async def get_db_connection() -> aiosqlite.Connection:
    db = await aiosqlite.connect(config.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    return db

async def init_db():
    """Initialize database tables and indexes."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        
        # 1. Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                referrer_id INTEGER,
                stickers_created INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Required channels for subscription verification
        await db.execute("""
            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                chat_id TEXT NOT NULL UNIQUE,
                invite_url TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                channel_type TEXT DEFAULT 'advertising',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Stickers history table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_id TEXT,
                has_outline INTEGER DEFAULT 1,
                removed_bg INTEGER DEFAULT 1,
                has_text INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            );
        """)

        # 4. User sticker packs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pack_name TEXT NOT NULL UNIQUE,
                pack_title TEXT NOT NULL,
                stickers_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            );
        """)

        # Indexes for fast lookup
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_stickers_user ON stickers(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_packs_user ON user_packs(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_channels_active ON required_channels(is_active);")

        await db.commit()
        logger.info("Database initialized successfully.")
