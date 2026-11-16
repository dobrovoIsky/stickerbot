from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main navigation keyboard."""
    keyboard = [
        [
            KeyboardButton(text="🎨 Створити стікер"),
            KeyboardButton(text="💬 Стікер із текстом")
        ],
        [
            KeyboardButton(text="📦 Мій стікерпак"),
            KeyboardButton(text="👥 Рефералка")
        ],
        [
            KeyboardButton(text="📖 Інструкція")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію або надішліть фото..."
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
