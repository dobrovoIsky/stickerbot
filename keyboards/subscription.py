from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import RequiredChannel

def get_subscription_keyboard(channels: list[RequiredChannel]) -> InlineKeyboardMarkup:
    """Creates inline keyboard with channel links and verification button."""
    buttons = []
    
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(text=f"📢 {ch.title}", url=ch.invite_url)
        ])
        
    buttons.append([
        InlineKeyboardButton(text="🔄 Перевірити підписку", callback_data="check_sub_retry")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
