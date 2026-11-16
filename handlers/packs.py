import os
import html
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from services.sticker_creator import add_sticker_to_user_pack
from keyboards.sticker_actions import get_pack_view_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "sticker_add_to_pack")
async def cb_add_to_pack(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or "User"
    data = await state.get_data()
    webp_path = data.get("temp_webp_path")

    if not webp_path or not os.path.exists(webp_path):
        await callback.answer("⚠️ Файл стікера застарів. Створи новий стікер.", show_alert=True)
        return

    await callback.answer("⏳ Додаю стікер до твого стікерпаку...")

    with open(webp_path, "rb") as f:
        webp_bytes = f.read()

    try:
        pack_name, pack_url, is_new = await add_sticker_to_user_pack(
            bot=callback.bot,
            user_id=user_id,
            user_name=user_name,
            webp_bytes=webp_bytes,
            emojis=["⭐"]
        )

        msg_title = "🎉 <b>Твій особистий стікерпак створено!</b>" if is_new else "✅ <b>Стікер додано до стікерпаку!</b>"
        text = f"""
{msg_title}

🔗 <b>Посилання на твій набір стікерів:</b>
<a href="{pack_url}">{pack_url}</a>

Натисни кнопку нижче, щоб встановити набір собі в Telegram та надіслати друзям! 🚀
"""
        await callback.message.answer(
            text,
            reply_markup=get_pack_view_keyboard(pack_url),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.exception(f"Error adding sticker to pack for user {user_id}: {e}")
        escaped_err = html.escape(str(e))
        await callback.message.answer(
            f"❌ Не вдалося додати стікер до паку.\n\n"
            f"<b>Помилка:</b> <code>{escaped_err}</code>\n\n"
            f"<i>Зверни увагу: стікери можуть додаватися лише якщо бот має валідний юзернейм і права на створення стікерів.</i>",
            parse_mode="HTML"
        )
