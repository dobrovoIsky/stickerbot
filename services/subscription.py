import time
import logging
from typing import Tuple, List, Dict
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from database.models import RequiredChannel
from database.queries import get_active_channels
from config import config

logger = logging.getLogger(__name__)

# Cache structure: { (user_id, channel_id): (is_member, expire_timestamp) }
_subscription_cache: Dict[Tuple[int, str], Tuple[bool, float]] = {}

def get_cached_status(user_id: int, channel_id: str) -> bool | None:
    cached = _subscription_cache.get((user_id, channel_id))
    if cached:
        is_member, expire_at = cached
        if time.time() < expire_at:
            return is_member
        else:
            del _subscription_cache[(user_id, channel_id)]
    return None

def set_cached_status(user_id: int, channel_id: str, is_member: bool):
    _subscription_cache[(user_id, channel_id)] = (
        is_member,
        time.time() + config.SUBSCRIPTION_CACHE_SECONDS
    )

def clear_user_cache(user_id: int):
    keys_to_delete = [k for k in _subscription_cache if k[0] == user_id]
    for k in keys_to_delete:
        del _subscription_cache[k]

async def check_user_subscriptions(bot: Bot, user_id: int, force_refresh: bool = False) -> Tuple[bool, List[RequiredChannel]]:
    """
    Checks if a user is subscribed to all active channels.
    Returns:
        (all_subscribed: bool, missing_channels: List[RequiredChannel])
    """
    if force_refresh:
        clear_user_cache(user_id)

    active_channels = await get_active_channels()
    if not active_channels:
        return True, []

    missing_channels: List[RequiredChannel] = []

    for channel in active_channels:
        # Check cache if not forcing refresh
        if not force_refresh:
            cached_result = get_cached_status(user_id, channel.chat_id)
            if cached_result is True:
                continue
            elif cached_result is False:
                missing_channels.append(channel)
                continue

        try:
            member = await bot.get_chat_member(
                chat_id=channel.chat_id,
                user_id=user_id
            )
            is_sub = member.status in ("creator", "administrator", "member")
            if not is_sub and member.status == "restricted":
                is_sub = getattr(member, "is_member", False)

            set_cached_status(user_id, channel.chat_id, is_sub)

            if not is_sub:
                missing_channels.append(channel)

        except TelegramAPIError as e:
            logger.warning(
                f"Error checking channel {channel.chat_id} ({channel.title}) for user {user_id}: {e}"
            )
            # If the bot cannot access the channel or chat not found,
            # we should not block the user, log warning and treat as passed
            set_cached_status(user_id, channel.chat_id, True)
        except Exception as e:
            logger.error(f"Unexpected error checking channel {channel.chat_id}: {e}")
            set_cached_status(user_id, channel.chat_id, True)

    return len(missing_channels) == 0, missing_channels
