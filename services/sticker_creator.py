import io
import asyncio
import logging
from typing import Optional, Tuple
from PIL import Image
from aiogram import Bot
from aiogram.types import BufferedInputFile, InputSticker
from services.background_remover import remove_background
from services.image_processor import add_sticker_outline, resize_for_sticker, add_text_to_image, convert_to_webp
from database.queries import get_user_pack, save_user_pack, increment_pack_stickers

logger = logging.getLogger(__name__)

async def process_sticker_image(
    image_bytes: bytes,
    remove_bg: bool = True,
    add_outline: bool = True,
    text: Optional[str] = None,
    text_pos: str = "bottom"
) -> bytes:
    """
    Full processing pipeline from raw image bytes to Telegram-ready WebP sticker bytes.
    """
    # 1. Background removal if requested
    if remove_bg:
        img = await remove_background(image_bytes)
    else:
        from PIL import ImageOps
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGBA")

    # 2. Add outline if requested and background was removed
    if add_outline and remove_bg:
        img = add_sticker_outline(img, outline_color=(255, 255, 255, 255), outline_width=10)

    # 3. Resize to 512px adhering to Telegram sticker specs first
    img = resize_for_sticker(img, max_size=512)

    # 4. Add text after resizing so bottom padding is preserved and not cropped out
    if text:
        img = add_text_to_image(img, text, position=text_pos)

    # 5. Convert to WebP
    return convert_to_webp(img)


def get_default_pack_name(user_id: int, bot_username: str) -> str:
    """Telegram requires sticker set name format: <name>_by_<bot_username>"""
    return f"u{user_id}_stickers_by_{bot_username.lower()}"

async def add_sticker_to_user_pack(
    bot: Bot,
    user_id: int,
    user_name: str,
    webp_bytes: bytes,
    emojis: list[str] = None
) -> Tuple[str, str, bool]:
    """
    Adds a sticker to the user's personal pack or creates one if it doesn't exist yet.
    Returns:
        (pack_name, pack_url, is_new_pack)
    """
    if emojis is None:
        emojis = ["⭐"]

    bot_info = await bot.get_me()
    bot_username = bot_info.username
    pack_name = get_default_pack_name(user_id, bot_username)
    pack_title = f"{user_name[:20]}'s Stickers"
    pack_url = f"https://t.me/addstickers/{pack_name}"

    input_sticker = InputSticker(
        sticker=BufferedInputFile(webp_bytes, filename="sticker.webp"),
        emoji_list=emojis,
        format="static"
    )

    existing_pack = await get_user_pack(user_id)

    # Try adding to existing set first if we know user has one
    if existing_pack:
        try:
            await bot.add_sticker_to_set(
                user_id=user_id,
                name=existing_pack.pack_name,
                sticker=input_sticker
            )
            await increment_pack_stickers(existing_pack.pack_name)
            return existing_pack.pack_name, f"https://t.me/addstickers/{existing_pack.pack_name}", False
        except Exception as e:
            logger.warning(f"Could not add sticker to existing pack {existing_pack.pack_name}: {e}. Trying create or fallback.")

    # Try creating new sticker set
    try:
        await bot.create_new_sticker_set(
            user_id=user_id,
            name=pack_name,
            title=pack_title,
            stickers=[input_sticker],
            sticker_format="static"
        )
        await save_user_pack(user_id, pack_name, pack_title, stickers_count=1)
        return pack_name, pack_url, True

    except Exception as e:
        # If set already exists on Telegram server, add to it
        error_msg = str(e).lower()
        if "short name is already taken" in error_msg or "set_already_exists" in error_msg or "already exists" in error_msg:
            try:
                await bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_name,
                    sticker=input_sticker
                )
                await save_user_pack(user_id, pack_name, pack_title, stickers_count=2)
                return pack_name, pack_url, False
            except Exception as add_err:
                logger.error(f"Failed to add sticker after duplicate check: {add_err}")
                raise add_err
        else:
            logger.error(f"Error creating sticker set: {e}")
            raise e
