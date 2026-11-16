from typing import Optional, List
from database.db import get_db_connection
from database.models import User, RequiredChannel, UserPack, BotStats

# --- USER QUERIES ---

async def get_or_create_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    referrer_id: Optional[int] = None
) -> tuple[User, bool]:
    """Returns (User, is_new_user)"""
    db = await get_db_connection()
    try:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE users SET username = ?, first_name = ?, last_active_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (username, first_name, user_id)
                )
                await db.commit()
                return User(
                    user_id=row["user_id"],
                    username=username or row["username"],
                    first_name=first_name or row["first_name"],
                    referrer_id=row["referrer_id"],
                    stickers_created=row["stickers_created"],
                    created_at=row["created_at"],
                    last_active_at=row["last_active_at"]
                ), False

        # If new user: avoid self-referral
        valid_referrer = referrer_id if (referrer_id and referrer_id != user_id) else None

        await db.execute(
            """INSERT INTO users (user_id, username, first_name, referrer_id)
               VALUES (?, ?, ?, ?)""",
            (user_id, username, first_name, valid_referrer)
        )
        await db.commit()

        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            new_row = await cursor.fetchone()
            return User(
                user_id=new_row["user_id"],
                username=new_row["username"],
                first_name=new_row["first_name"],
                referrer_id=new_row["referrer_id"],
                stickers_created=new_row["stickers_created"],
                created_at=new_row["created_at"],
                last_active_at=new_row["last_active_at"]
            ), True
    finally:
        await db.close()

async def update_user_activity(user_id: int):
    db = await get_db_connection()
    try:
        await db.execute(
            "UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
    finally:
        await db.close()

async def increment_user_stickers(user_id: int):
    db = await get_db_connection()
    try:
        await db.execute(
            "UPDATE users SET stickers_created = stickers_created + 1, last_active_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
    finally:
        await db.close()

async def get_user_referrals_count(user_id: int) -> int:
    db = await get_db_connection()
    try:
        async with db.execute("SELECT COUNT(*) as count FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row["count"] if row else 0
    finally:
        await db.close()

# --- CHANNEL QUERIES ---

async def get_active_channels() -> List[RequiredChannel]:
    db = await get_db_connection()
    try:
        async with db.execute(
            "SELECT * FROM required_channels WHERE is_active = 1 ORDER BY channel_type DESC, id ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                RequiredChannel(
                    id=r["id"],
                    title=r["title"],
                    chat_id=r["chat_id"],
                    invite_url=r["invite_url"],
                    is_active=bool(r["is_active"]),
                    channel_type=r["channel_type"],
                    created_at=r["created_at"]
                ) for r in rows
            ]
    finally:
        await db.close()

async def get_all_channels() -> List[RequiredChannel]:
    db = await get_db_connection()
    try:
        async with db.execute("SELECT * FROM required_channels ORDER BY id ASC") as cursor:
            rows = await cursor.fetchall()
            return [
                RequiredChannel(
                    id=r["id"],
                    title=r["title"],
                    chat_id=r["chat_id"],
                    invite_url=r["invite_url"],
                    is_active=bool(r["is_active"]),
                    channel_type=r["channel_type"],
                    created_at=r["created_at"]
                ) for r in rows
            ]
    finally:
        await db.close()

async def add_channel(title: str, chat_id: str, invite_url: str, channel_type: str = "advertising") -> int:
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            """INSERT INTO required_channels (title, chat_id, invite_url, channel_type, is_active)
               VALUES (?, ?, ?, ?, 1)
               ON CONFLICT(chat_id) DO UPDATE SET title = excluded.title, invite_url = excluded.invite_url, is_active = 1, channel_type = excluded.channel_type""",
            (title, chat_id, invite_url, channel_type)
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()

async def remove_channel(channel_id: int) -> bool:
    db = await get_db_connection()
    try:
        cursor = await db.execute("DELETE FROM required_channels WHERE id = ?", (channel_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()

async def toggle_channel(channel_id: int) -> Optional[bool]:
    db = await get_db_connection()
    try:
        async with db.execute("SELECT is_active FROM required_channels WHERE id = ?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            new_status = 0 if row["is_active"] else 1
        
        await db.execute("UPDATE required_channels SET is_active = ? WHERE id = ?", (new_status, channel_id))
        await db.commit()
        return bool(new_status)
    finally:
        await db.close()

# --- STICKER & PACK QUERIES ---

async def record_sticker(user_id: int, file_id: str = "", has_outline: bool = True, removed_bg: bool = True, has_text: bool = False):
    db = await get_db_connection()
    try:
        await db.execute(
            """INSERT INTO stickers (user_id, file_id, has_outline, removed_bg, has_text)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, file_id, int(has_outline), int(removed_bg), int(has_text))
        )
        await db.execute(
            "UPDATE users SET stickers_created = stickers_created + 1, last_active_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
    finally:
        await db.close()

async def get_user_pack(user_id: int) -> Optional[UserPack]:
    db = await get_db_connection()
    try:
        async with db.execute("SELECT * FROM user_packs WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return UserPack(
                    id=row["id"],
                    user_id=row["user_id"],
                    pack_name=row["pack_name"],
                    pack_title=row["pack_title"],
                    stickers_count=row["stickers_count"],
                    created_at=row["created_at"]
                )
            return None
    finally:
        await db.close()

async def save_user_pack(user_id: int, pack_name: str, pack_title: str, stickers_count: int = 1) -> UserPack:
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            """INSERT INTO user_packs (user_id, pack_name, pack_title, stickers_count)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(pack_name) DO UPDATE SET stickers_count = excluded.stickers_count, pack_title = excluded.pack_title""",
            (user_id, pack_name, pack_title, stickers_count)
        )
        await db.commit()
        return UserPack(
            id=cursor.lastrowid or 0,
            user_id=user_id,
            pack_name=pack_name,
            pack_title=pack_title,
            stickers_count=stickers_count,
            created_at=""
        )
    finally:
        await db.close()

async def increment_pack_stickers(pack_name: str):
    db = await get_db_connection()
    try:
        await db.execute("UPDATE user_packs SET stickers_count = stickers_count + 1 WHERE pack_name = ?", (pack_name,))
        await db.commit()
    finally:
        await db.close()

# --- STATS & ADMIN ---

async def get_stats() -> BotStats:
    db = await get_db_connection()
    try:
        async with db.execute("SELECT COUNT(*) as total FROM users") as cur:
            total_users = (await cur.fetchone())["total"]
        
        async with db.execute("SELECT COUNT(*) as active FROM users WHERE date(last_active_at) = date('now')") as cur:
            active_today = (await cur.fetchone())["active"]

        async with db.execute("SELECT COUNT(*) as total_s FROM stickers") as cur:
            total_stickers = (await cur.fetchone())["total_s"]

        async with db.execute("SELECT COUNT(*) as total_p FROM user_packs") as cur:
            total_packs = (await cur.fetchone())["total_p"]

        async with db.execute("SELECT COUNT(*) as refs FROM users WHERE referrer_id IS NOT NULL") as cur:
            total_referrals = (await cur.fetchone())["refs"]

        return BotStats(
            total_users=total_users,
            active_today=active_today,
            total_stickers=total_stickers,
            total_packs=total_packs,
            total_referrals=total_referrals
        )
    finally:
        await db.close()

async def get_all_user_ids() -> List[int]:
    db = await get_db_connection()
    try:
        async with db.execute("SELECT user_id FROM users") as cur:
            rows = await cur.fetchall()
            return [r["user_id"] for r in rows]
    finally:
        await db.close()
