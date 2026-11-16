from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import RequiredChannel

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Канали підписок", callback_data="admin_channels")
        ],
        [
            InlineKeyboardButton(text="➕ Додати канал", callback_data="admin_add_channel"),
            InlineKeyboardButton(text="✉️ Розсилка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="🔄 Оновити", callback_data="admin_refresh")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_channels_management_keyboard(channels: list[RequiredChannel]) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        status_icon = "🟢" if ch.is_active else "🔴"
        type_icon = "⭐ [Власний]" if ch.channel_type == "own" else "💼 [Реклама]"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} {ch.title} {type_icon}",
                callback_data=f"adm_ch_view:{ch.id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="➕ Додати новий канал", callback_data="admin_add_channel")
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад в адмінку", callback_data="admin_back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_channel_detail_keyboard(channel: RequiredChannel) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Вимкнути перевірку" if channel.is_active else "🟢 Увімкнути перевірку"
    buttons = [
        [
            InlineKeyboardButton(text=toggle_text, callback_data=f"adm_ch_toggle:{channel.id}")
        ],
        [
            InlineKeyboardButton(text="🗑 Видалити канал", callback_data=f"adm_ch_delete:{channel.id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад до списку", callback_data="admin_channels")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
