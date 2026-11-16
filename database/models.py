from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    referrer_id: Optional[int]
    stickers_created: int
    created_at: str
    last_active_at: str

@dataclass
class RequiredChannel:
    id: int
    title: str
    chat_id: str
    invite_url: str
    is_active: bool
    channel_type: str  # 'own' or 'advertising'
    created_at: str

@dataclass
class UserPack:
    id: int
    user_id: int
    pack_name: str
    pack_title: str
    stickers_count: int
    created_at: str

@dataclass
class BotStats:
    total_users: int
    active_today: int
    total_stickers: int
    total_packs: int
    total_referrals: int
