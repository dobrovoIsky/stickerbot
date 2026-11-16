import io
import asyncio
import logging
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Cache rembg session
_rembg_session = None

def get_session():
    global _rembg_session
    if _rembg_session is None:
        try:
            import onnxruntime as ort
            from rembg import new_session
            
            # Configure ONNX session options for low CPU usage
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 1
            opts.inter_op_num_threads = 1
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            
            _rembg_session = new_session("u2netp", providers=["CPUExecutionProvider"], session_options=opts)
            logger.info("rembg u2netp session initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize custom rembg session with options: {e}")
            try:
                from rembg import new_session
                _rembg_session = new_session("u2netp")
            except Exception as e2:
                logger.error(f"Fallback rembg session failed: {e2}")
                _rembg_session = False
    return _rembg_session if _rembg_session is not False else None

def _remove_bg_sync(image_bytes: bytes) -> Image.Image:
    """
    Optimized background removal:
    1. Transposes phone EXIF orientation so images aren't rotated sideways.
    2. Pre-downscales giant phone photos (4000x3000 -> 768x768) which speeds up
       processing by 16x without any loss for 512px Telegram stickers.
    3. Uses pre-initialized u2netp session.
    """
    try:
        raw_img = Image.open(io.BytesIO(image_bytes))
        # Correct orientation if phone camera added EXIF rotation tag
        raw_img = ImageOps.exif_transpose(raw_img)
        raw_img = raw_img.convert("RGB")

        # Crucial optimization: downscale giant phone photos to max 768px before AI
        max_dim = max(raw_img.size)
        if max_dim > 768:
            raw_img.thumbnail((768, 768), Image.Resampling.BILINEAR)

        import rembg
        session = get_session()
        if session:
            out_img = rembg.remove(raw_img, session=session)
        else:
            out_img = rembg.remove(raw_img)

        return out_img.convert("RGBA")

    except ImportError:
        logger.error("rembg is not installed. Background removal is skipped.")
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        logger.exception(f"Error removing background: {e}")
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

async def remove_background(image_bytes: bytes) -> Image.Image:
    """Runs rembg background removal asynchronously in a worker thread."""
    return await asyncio.to_thread(_remove_bg_sync, image_bytes)
