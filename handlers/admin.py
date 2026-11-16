import asyncio
import html
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import config
from database.queries import (
    get_stats, get_all_channels, add_channel, remove_channel,
    toggle_channel, get_all_user_ids
)
from keyboards.admin_kb import (
    get_admin_main_keyboard,
    get_channels_management_keyboard,
    get_channel_detail_keyboard
)

router = Router()
logger = logging.getLogger(__name__)

class AdminStates(StatesGroup):
    waiting_for_channel_info = State()
    waiting_for_broadcast_msg = State()

def is_admin(user_id: int) -> bool:
    if not config.ADMIN_IDS:
        return True  # If no admin configured, permit user to configure
    return user_id in config.ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return

    text = f"""
👑 <b>Панель адміністратора Sticker Factory</b>

ID вашого акаунту: <code>{message.from_user.id}</code>
У конфігурації адміністраторів: <code>{config.ADMIN_IDS}</code>

Оберіть необхідний розділ:
"""
    await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_refresh")
@router.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    text = f"""
👑 <b>Панель адміністратора Sticker Factory</b>

ID вашого акаунту: <code>{callback.from_user.id}</code>
У конфігурації адміністраторів: <code>{config.ADMIN_IDS}</code>

Оберіть необхідний розділ:
"""
    await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")

@router.message(Command("stats"))
@router.callback_query(F.data == "admin_stats")
async def handle_stats(event: Message | CallbackQuery):
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    stats = await get_stats()
    text = f"""
📊 <b>Статистика бота Sticker Factory:</b>

👥 Усього користувачів: <b>{stats.total_users}</b>
🔥 Активних сьогодні: <b>{stats.active_today}</b>
🎨 Створено стікерів: <b>{stats.total_stickers}</b>
📦 Створено стікерпаків: <b>{stats.total_packs}</b>
🔗 Залучено через рефералів: <b>{stats.total_referrals}</b>
"""
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, parse_mode="HTML")
    else:
        await event.answer(text, parse_mode="HTML")

@router.message(Command("channels"))
@router.callback_query(F.data == "admin_channels")
async def handle_channels_list(event: Message | CallbackQuery):
    user_id = event.from_user.id
    if not is_admin(user_id):
        return

    channels = await get_all_channels()
    text = f"""
📢 <b>Обов'язкові канали для перевірки підписки:</b>
Усього підключено каналів: <code>{len(channels)}</code>

🟢 - канал активний
🔴 - канал вимкнено (перевірка не проводиться)

Натисніть на канал для налаштування або додайте новий:
"""
    kb = get_channels_management_keyboard(channels)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_ch_view:"))
async def cb_view_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    channel_id = int(callback.data.split(":")[1])
    channels = await get_all_channels()
    target_ch = next((c for c in channels if c.id == channel_id), None)

    if not target_ch:
        await callback.answer("Канал не знайдено.", show_alert=True)
        return

    status = "🟢 Активний" if target_ch.is_active else "🔴 Вимкнений"
    ch_type = "⭐ Власний канал проекту" if target_ch.channel_type == "own" else "💼 Рекламний спонсор"

    escaped_title = html.escape(target_ch.title)
    escaped_url = html.escape(target_ch.invite_url)
    text = f"""
📢 <b>Налаштування каналу #{target_ch.id}:</b>

🏷 Назва: <b>{escaped_title}</b>
🆔 Telegram ID / Username: <code>{target_ch.chat_id}</code>
🔗 Посилання: <a href="{escaped_url}">{escaped_url}</a>
📂 Тип: {ch_type}
🚦 Статус перевірки: <b>{status}</b>
"""
    await callback.message.edit_text(
        text,
        reply_markup=get_channel_detail_keyboard(target_ch),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@router.callback_query(F.data.startswith("adm_ch_toggle:"))
async def cb_toggle_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    channel_id = int(callback.data.split(":")[1])
    new_status = await toggle_channel(channel_id)
    await callback.answer(f"Статус змінено на: {'Активний' if new_status else 'Вимкнений'}")
    
    # Re-display channel
    channels = await get_all_channels()
    target_ch = next((c for c in channels if c.id == channel_id), None)
    if target_ch:
        await callback.message.edit_reply_markup(reply_markup=get_channel_detail_keyboard(target_ch))

@router.callback_query(F.data.startswith("adm_ch_delete:"))
async def cb_delete_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    channel_id = int(callback.data.split(":")[1])
    await remove_channel(channel_id)
    await callback.answer("Канал видалено з бази!", show_alert=True)

    channels = await get_all_channels()
    await callback.message.edit_text(
        f"📢 Канал видалено. Поточних каналів: <code>{len(channels)}</code>",
        reply_markup=get_channels_management_keyboard(channels),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_add_channel")
async def cb_prompt_add_channel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_channel_info)
    await callback.answer()
    await callback.message.answer(
        "➕ <b>Додавання обов'язкового каналу</b>\n\n"
        "Надішліть дані каналу в одному повідомленні через кому або з нового рядка:\n"
        "<code>Назва, Telegram Chat ID або @username, Посилання-запрошення, Тип (own або advertising)</code>\n\n"
        "Приклад:\n"
        "<code>Мій Канал, @mychannel, https://t.me/mychannel, own</code>\n\n"
        "⚠️ <i>Переконайтесь, що бот доданий адміністратором у цей канал!</i>",
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_for_channel_info)
async def handle_channel_data_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    lines = [p.strip() for p in message.text.replace("\n", ",").split(",") if p.strip()]
    if len(lines) < 3:
        await message.answer("❌ Некоректний формат. Потрібно вказати: <code>Назва, Chat_ID/@username, Посилання, [тип]</code>", parse_mode="HTML")
        return

    title = lines[0]
    chat_id = lines[1]
    invite_url = lines[2]
    channel_type = lines[3].lower() if len(lines) > 3 and lines[3].lower() in ("own", "advertising") else "advertising"

    try:
        await add_channel(title=title, chat_id=chat_id, invite_url=invite_url, channel_type=channel_type)
        await state.clear()
        escaped_title = html.escape(title)
        await message.answer(
            f"✅ <b>Канал «{escaped_title}» успішно додано!</b>\nВін з'явився у системі перевірки підписок.",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception("Error adding channel")
        escaped_err = html.escape(str(e))
        await message.answer(f"❌ Помилка додавання: <code>{escaped_err}</code>", parse_mode="HTML")

@router.callback_query(F.data == "admin_broadcast")
async def cb_prompt_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    await callback.answer()
    await callback.message.answer(
        "✉️ <b>Розсилка повідомлення</b>\n\n"
        "Надішліть повідомлення (текст, фото або відео), яке потрібно розіслати всім користувачам бота:",
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_for_broadcast_msg)
async def handle_broadcast_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    status_msg = await message.answer("🚀 Починаю розсилку...")

    user_ids = await get_all_user_ids()
    total = len(user_ids)
    success = 0
    failed = 0

    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            success += 1
            await asyncio.sleep(0.05)  # Rate limiting safeguard
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Розсилку завершено!</b>\n\n"
        f"📊 Усього користувачів: <code>{total}</code>\n"
        f"✔️ Успішно доставлено: <code>{success}</code>\n"
        f"❌ Не доставлено (заблоковано): <code>{failed}</code>",
        parse_mode="HTML"
    )
