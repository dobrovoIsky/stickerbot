import io
import os
import uuid
import html
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.subscription import check_user_subscriptions
from services.sticker_creator import process_sticker_image
from database.queries import record_sticker
from keyboards.subscription import get_subscription_keyboard
from keyboards.main_menu import get_main_menu_keyboard, get_cancel_keyboard
from keyboards.sticker_actions import get_sticker_options_keyboard
from config import config

router = Router()
logger = logging.getLogger(__name__)

class StickerStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_text = State()
    preview_mode = State()

@router.message(F.text == "🎨 Створити стікер")
async def start_sticker_flow(message: Message, state: FSMContext):
    # Check subscriptions
    is_sub, missing = await check_user_subscriptions(message.bot, message.from_user.id)
    if not is_sub:
        await message.answer(
            "⚠️ <b>Для створення стікерів необхідно підписатися на канали партнерів:</b>",
            reply_markup=get_subscription_keyboard(missing),
            parse_mode="HTML"
        )
        return

    await state.set_state(StickerStates.waiting_for_photo)
    await state.update_data(with_text=False)
    await message.answer(
        "📸 <b>Надішли мені фотографію</b> (як фото або документ без стиснення):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "💬 Стікер із текстом")
async def start_text_sticker_flow(message: Message, state: FSMContext):
    is_sub, missing = await check_user_subscriptions(message.bot, message.from_user.id)
    if not is_sub:
        await message.answer(
            "⚠️ <b>Для створення стікерів необхідно підписатися на канали партнерів:</b>",
            reply_markup=get_subscription_keyboard(missing),
            parse_mode="HTML"
        )
        return

    await state.set_state(StickerStates.waiting_for_photo)
    await state.update_data(with_text=True)
    await message.answer(
        "📸 <b>Надішли мені фотографію</b>, до якої хочеш додати напис:\n"
        "<i>(Можна одразу додати підпис до фотографії, і він стане текстом стікера)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )

async def download_image(message: Message) -> bytes | None:
    """Downloads photo or image document from message."""
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        file_id = message.document.file_id
    
    if not file_id:
        return None

    file_info = await message.bot.get_file(file_id)
    if file_info.file_size and file_info.file_size > config.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        await message.answer(f"❌ Файл занадто великий. Максимальний розмір — {config.MAX_IMAGE_SIZE_MB} МБ.")
        return None

    file_stream = io.BytesIO()
    await message.bot.download_file(file_info.file_path, destination=file_stream)
    return file_stream.getvalue()

@router.message(F.photo | (F.document & F.document.mime_type.startswith("image/")))
async def handle_incoming_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # 1. Check subscriptions dynamically before image processing
    is_sub, missing = await check_user_subscriptions(message.bot, user_id)
    if not is_sub:
        await message.answer(
            "⚠️ <b>Для створення стікерів необхідно підписатися на канали партнерів:</b>",
            reply_markup=get_subscription_keyboard(missing),
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer("⏳ <b>Завантажую та обробляю фотографію...</b>", parse_mode="HTML")

    raw_bytes = await download_image(message)
    if not raw_bytes:
        await status_msg.edit_text("❌ Не вдалося отримати зображення. Спробуй надіслати інше фото.")
        return

    state_data = await state.get_data()
    caption_text = message.caption or state_data.get("sticker_text")

    # If user selected "Стікер із текстом" but provided no caption, ask for text
    if state_data.get("with_text") and not caption_text:
        # Save raw bytes to temp file
        temp_filename = f"raw_{uuid.uuid4().hex}.png"
        temp_path = os.path.join(config.TEMP_DIR, temp_filename)
        with open(temp_path, "wb") as f:
            f.write(raw_bytes)

        await state.update_data(
            temp_raw_path=temp_path,
            has_outline=True,
            remove_bg=True
        )
        await state.set_state(StickerStates.waiting_for_text)
        await status_msg.delete()
        await message.answer(
            "💬 <b>Фото отримано! Тепер напиши текст</b>, який хочеш бачити на стікері:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    # Default settings
    has_outline = True
    remove_bg = True

    try:
        await status_msg.edit_text("✨ <b>Видаляю фон та оптимізую розмір...</b>", parse_mode="HTML")
        webp_bytes = await process_sticker_image(
            image_bytes=raw_bytes,
            remove_bg=remove_bg,
            add_outline=has_outline,
            text=caption_text
        )

        # Save raw and processed sticker to temp directory
        unique_id = uuid.uuid4().hex
        raw_path = os.path.join(config.TEMP_DIR, f"raw_{unique_id}.png")
        webp_path = os.path.join(config.TEMP_DIR, f"sticker_{unique_id}.webp")

        with open(raw_path, "wb") as f:
            f.write(raw_bytes)
        with open(webp_path, "wb") as f:
            f.write(webp_bytes)

        await status_msg.delete()

        # Send sticker to user
        sticker_file = BufferedInputFile(webp_bytes, filename="sticker.webp")
        sent_sticker = await message.answer_sticker(sticker=sticker_file)

        # Store in FSM
        await state.set_state(StickerStates.preview_mode)
        await state.update_data(
            temp_raw_path=raw_path,
            temp_webp_path=webp_path,
            has_outline=has_outline,
            remove_bg=remove_bg,
            sticker_text=caption_text,
            last_sticker_file_id=sent_sticker.sticker.file_id
        )

        # Record in database
        await record_sticker(
            user_id=user_id,
            file_id=sent_sticker.sticker.file_id,
            has_outline=has_outline,
            removed_bg=remove_bg,
            has_text=bool(caption_text)
        )

        # Send controls
        await message.answer(
            "🎉 <b>Твій стікер готовий!</b>\n"
            "Ти можеш змінити налаштування або додати його до свого стікерпаку:",
            reply_markup=get_sticker_options_keyboard(
                has_outline=has_outline,
                removed_bg=remove_bg,
                has_text=bool(caption_text)
            ),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.exception(f"Error processing sticker: {e}")
        await status_msg.edit_text("❌ Виникла помилка під час обробки фото. Будь ласка, спробуй інше фото.")

@router.message(StickerStates.waiting_for_text)
async def handle_text_input(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=get_main_menu_keyboard())
        return

    text = message.text.strip()
    data = await state.get_data()
    raw_path = data.get("temp_raw_path")

    if not raw_path or not os.path.exists(raw_path):
        await message.answer("⚠️ Зображення застаріло. Надішли нове фото, будь ласка.", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return

    status_msg = await message.answer("⏳ <b>Генерую стікер із твоїм текстом...</b>", parse_mode="HTML")

    with open(raw_path, "rb") as f:
        raw_bytes = f.read()

    has_outline = data.get("has_outline", True)
    remove_bg = data.get("remove_bg", True)

    try:
        webp_bytes = await process_sticker_image(
            image_bytes=raw_bytes,
            remove_bg=remove_bg,
            add_outline=has_outline,
            text=text
        )

        unique_id = uuid.uuid4().hex
        webp_path = os.path.join(config.TEMP_DIR, f"sticker_{unique_id}.webp")
        with open(webp_path, "wb") as f:
            f.write(webp_bytes)

        await status_msg.delete()
        sent_sticker = await message.answer_sticker(sticker=BufferedInputFile(webp_bytes, filename="sticker.webp"))

        await state.set_state(StickerStates.preview_mode)
        await state.update_data(
            temp_webp_path=webp_path,
            sticker_text=text,
            last_sticker_file_id=sent_sticker.sticker.file_id
        )

        await record_sticker(
            user_id=message.from_user.id,
            file_id=sent_sticker.sticker.file_id,
            has_outline=has_outline,
            removed_bg=remove_bg,
            has_text=True
        )

        await message.answer(
            "🎉 <b>Стікер оновлено!</b>",
            reply_markup=get_sticker_options_keyboard(
                has_outline=has_outline,
                removed_bg=remove_bg,
                has_text=True
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Error applying text to sticker: {e}")
        await status_msg.edit_text("❌ Помилка обробки. Спробуй ще раз.")

@router.callback_query(F.data == "sticker_toggle_outline")
async def cb_toggle_outline(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    raw_path = data.get("temp_raw_path")
    if not raw_path or not os.path.exists(raw_path):
        await callback.answer("⚠️ Сесія застаріла. Надішли фото знову.", show_alert=True)
        return

    new_outline = not data.get("has_outline", True)
    remove_bg = data.get("remove_bg", True)
    text = data.get("sticker_text")

    await callback.answer("⏳ Оновлюю контур...")

    with open(raw_path, "rb") as f:
        raw_bytes = f.read()

    webp_bytes = await process_sticker_image(
        image_bytes=raw_bytes,
        remove_bg=remove_bg,
        add_outline=new_outline,
        text=text
    )

    webp_path = data.get("temp_webp_path") or os.path.join(config.TEMP_DIR, f"sticker_{uuid.uuid4().hex}.webp")
    with open(webp_path, "wb") as f:
        f.write(webp_bytes)

    await state.update_data(has_outline=new_outline, temp_webp_path=webp_path)

    sent_sticker = await callback.message.answer_sticker(sticker=BufferedInputFile(webp_bytes, filename="sticker.webp"))
    await state.update_data(last_sticker_file_id=sent_sticker.sticker.file_id)

    await callback.message.answer(
        "✨ <b>Вигляд оновлено!</b>",
        reply_markup=get_sticker_options_keyboard(
            has_outline=new_outline,
            removed_bg=remove_bg,
            has_text=bool(text)
        ),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "sticker_toggle_bg")
async def cb_toggle_bg(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    raw_path = data.get("temp_raw_path")
    if not raw_path or not os.path.exists(raw_path):
        await callback.answer("⚠️ Сесія застаріла. Надішли фото знову.", show_alert=True)
        return

    new_remove_bg = not data.get("remove_bg", True)
    has_outline = data.get("has_outline", True)
    text = data.get("sticker_text")

    await callback.answer("⏳ Змінюю режим фону...")

    with open(raw_path, "rb") as f:
        raw_bytes = f.read()

    webp_bytes = await process_sticker_image(
        image_bytes=raw_bytes,
        remove_bg=new_remove_bg,
        add_outline=has_outline,
        text=text
    )

    webp_path = data.get("temp_webp_path") or os.path.join(config.TEMP_DIR, f"sticker_{uuid.uuid4().hex}.webp")
    with open(webp_path, "wb") as f:
        f.write(webp_bytes)

    await state.update_data(remove_bg=new_remove_bg, temp_webp_path=webp_path)

    sent_sticker = await callback.message.answer_sticker(sticker=BufferedInputFile(webp_bytes, filename="sticker.webp"))
    await state.update_data(last_sticker_file_id=sent_sticker.sticker.file_id)

    await callback.message.answer(
        "✨ <b>Вигляд оновлено!</b>",
        reply_markup=get_sticker_options_keyboard(
            has_outline=has_outline,
            removed_bg=new_remove_bg,
            has_text=bool(text)
        ),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "sticker_add_text")
async def cb_prompt_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StickerStates.waiting_for_text)
    await callback.answer()
    await callback.message.answer(
        "💬 <b>Введи текст</b>, який хочеш додати на цей стікер:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "sticker_create_new")
async def cb_create_new(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(StickerStates.waiting_for_photo)
    await callback.answer()
    await callback.message.answer(
        "📸 <b>Надішли мені нове фото</b>:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
