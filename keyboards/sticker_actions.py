from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_sticker_options_keyboard(
    has_outline: bool = True,
    removed_bg: bool = True,
    has_text: bool = False
) -> InlineKeyboardMarkup:
    """Action buttons attached to generated sticker."""
    outline_text = "⚪ Обводка: Увімкнена" if has_outline else "⚫ Обводка: Вимкнена"
    bg_text = "✨ Фон: Видалено" if removed_bg else "🖼 Фон: Збережено"
    text_btn = "✏️ Змінити текст" if has_text else "💬 Додати текст"

    buttons = [
        [
            InlineKeyboardButton(text="➕ Додати до стікерпаку", callback_data="sticker_add_to_pack")
        ],
        [
            InlineKeyboardButton(text=outline_text, callback_data="sticker_toggle_outline"),
            InlineKeyboardButton(text=bg_text, callback_data="sticker_toggle_bg")
        ],
        [
            InlineKeyboardButton(text=text_btn, callback_data="sticker_add_text")
        ],
        [
            InlineKeyboardButton(text="🚀 Створити новий", callback_data="sticker_create_new")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_pack_view_keyboard(pack_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Відкрити стікерпак в Telegram", url=pack_url)],
            [InlineKeyboardButton(text="🎨 Додати новий стікер", callback_data="sticker_create_new")]
        ]
    )
