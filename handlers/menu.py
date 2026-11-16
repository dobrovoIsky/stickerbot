import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.queries import get_user_pack, get_user_referrals_count
from keyboards.main_menu import get_main_menu_keyboard
from keyboards.sticker_actions import get_pack_view_keyboard

router = Router()

INSTRUCTION_TEXT = """
📖 <b>Як користуватися Sticker Factory:</b>

1️⃣ <b>Надішли фотографію</b> — бот автоматично:
   • Виріже головний об'єкт та прибере фон
   • Додасть фірмову білу обводку стікера
   • Оптимізує розмір до стандарту Telegram (512x512)

2️⃣ <b>Налаштуй вигляд</b>:
   • За бажанням можна вимкнути обводку або залишити оригінальний фон
   • Можна додати будь-який напис (мем) на стікер

3️⃣ <b>Додай до стікерпаку</b>:
   • Натисни «➕ Додати до стікерпаку»
   • Бот створить персональний набір стікерів або додасть новий стікер до вже існуючого!
   • Посилання на твій стікерпак можна надіслати друзям! 🎉
"""

@router.message(F.text == "📖 Інструкція")
async def cmd_instruction(message: Message):
    await message.answer(
        INSTRUCTION_TEXT,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(F.text == "👥 Рефералка")
async def cmd_referral(message: Message):
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    refs_count = await get_user_referrals_count(user_id)

    text = f"""
👥 <b>Реферальна програма</b>

Поділись ботом із друзями та створюйте спільні стікери разом! 🌟

🔗 <b>Твоє персональне посилання:</b>
<code>{html.escape(ref_link)}</code>

📊 <b>Запрошено друзів:</b> <code>{refs_count}</code>

💡 <i>Коли твої друзі переходять за цим посиланням, вони автоматично закріплюються за тобою.</i>
"""
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📦 Мій стікерпак")
async def cmd_my_pack(message: Message):
    user_id = message.from_user.id
    pack = await get_user_pack(user_id)

    if not pack:
        await message.answer(
            "📦 <b>У тебе ще немає створеного стікерпаку.</b>\n\n"
            "Надішли мені будь-яке фото, створи свій перший стікер і натисни кнопку <b>«➕ Додати до стікерпаку»</b>!",
            parse_mode="HTML"
        )
        return

    pack_url = f"https://t.me/addstickers/{pack.pack_name}"
    escaped_title = html.escape(pack.pack_title)
    text = f"""
📦 <b>Твій персональний стікерпак:</b>
📌 Назва: <b>{escaped_title}</b>
🔢 Кількість стікерів у наборі: <code>{pack.stickers_count}</code>

👉 <b>Посилання для встановлення:</b>
<a href="{pack_url}">{pack_url}</a>
"""
    await message.answer(
        text,
        reply_markup=get_pack_view_keyboard(pack_url),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@router.message(F.text == "❌ Скасувати")
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    await message.answer("Дію скасовано. Повертаємось у головне меню.", reply_markup=get_main_menu_keyboard())
