import io
import asyncio
import logging
from PIL import Image

logger = logging.getLogger(__name__)

# Cache rembg session if available
_rembg_session = None

def _get_session():
    global _rembg_session
    if _rembg_session is None:
        try:
            from rembg import new_session
            # u2net or isnet-general-use or silueta
            _rembg_session = new_session("u2netp") # lighter and fast u2netp or standard u2net
        except Exception as e:
            logger.warning(f"Could not initialize custom rembg session: {e}")
            _rembg_session = False
    return _rembg_session if _rembg_session is not False else None

def _remove_bg_sync(image_bytes: bytes) -> bytes:
    try:
        import rembg
        session = _get_session()
        if session:
            output_bytes = rembg.remove(image_bytes, session=session)
        else:
            output_bytes = rembg.remove(image_bytes)
        return output_bytes
    except ImportError:
        logger.error("rembg is not installed. Background removal is skipped.")
        return image_bytes
    except Exception as e:
        logger.exception(f"Error removing background: {e}")
        return image_bytes

async def remove_background(image_bytes: bytes) -> bytes:
    """Runs rembg background removal in a separate thread."""
    return await asyncio.to_thread(_remove_bg_sync, image_bytes)
