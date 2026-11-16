import html
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from database.queries import get_or_create_user, get_user_referrals_count
from services.subscription import check_user_subscriptions
from keyboards.main_menu import get_main_menu_keyboard
from keyboards.subscription import get_subscription_keyboard

router = Router()
logger = logging.getLogger(__name__)

WELCOME_TEXT = """
👋 <b>Привіт, {name}!</b>

Ласкаво просимо до <b>Sticker Factory</b> — твого швидкого генератора крутих стікерів для Telegram! 🚀

🎨 <b>Що вміє цей бот:</b>
• ✂️ Миттєво видаляє фон з будь-якого фото
• ⚪ Додає стильний білий контур стікера
• 💬 Накладає кумедний текст або меми
• 📦 Автоматично формує твій особистий стікерпак

📸 Просто надішли мені будь-яке фото, і я зроблю з нього стікер!
"""

SUBSCRIPTION_REQUIRED_TEXT = """
⚠️ <b>Для доступу до безкоштовного створення стікерів:</b>

Будь ласка, підпишись на канали наших партнерів та наш офіційний канал. Це допомагає підтримувати сервер та роботу безкоштовного AI.

👇 Підпишись на канали нижче та натисни кнопку <b>«🔄 Перевірити підписку»</b>:
"""

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = html.escape(message.from_user.first_name or "Друже")

    # Extract referrer if present (e.g. /start ref_123456)
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            ref_str = command.args.replace("ref_", "")
            referrer_id = int(ref_str)
        except ValueError:
            pass

    user, is_new = await get_or_create_user(
        user_id=user_id,
        username=username,
        first_name=first_name,
        referrer_id=referrer_id
    )

    if is_new and referrer_id:
        logger.info(f"New user {user_id} invited by {referrer_id}")

    # Check subscriptions
    is_subscribed, missing_channels = await check_user_subscriptions(message.bot, user_id)
    if not is_subscribed:
        await message.answer(
            SUBSCRIPTION_REQUIRED_TEXT,
            reply_markup=get_subscription_keyboard(missing_channels),
            parse_mode="HTML"
        )
        return

    await message.answer(
        WELCOME_TEXT.format(name=first_name),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "check_sub_retry")
async def cb_check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed, missing_channels = await check_user_subscriptions(callback.bot, user_id, force_refresh=True)

    if is_subscribed:
        await callback.answer("✅ Підписку підтверджено! Ласкаво просимо!", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        escaped_name = html.escape(callback.from_user.first_name or "Друже")
        await callback.message.answer(
            WELCOME_TEXT.format(name=escaped_name),
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.answer(
            "❌ Ви ще не підписалися на всі канали! Будь ласка, перевірте підписки.",
            show_alert=True
        )
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_subscription_keyboard(missing_channels)
            )
        except Exception:
            pass
