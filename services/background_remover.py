import io
import time
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
            
            # Configure ONNX session options strictly for single-threaded CPU
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 1
            opts.inter_op_num_threads = 1
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            
            _rembg_session = new_session("u2netp", sess_opts=opts)
            logger.info("rembg u2netp session initialized successfully with 1-thread CPU options.")
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
    Optimized background removal for Render Free tier (0.1 CPU / 512MB RAM):
    1. Fix phone EXIF rotation.
    2. Downscale directly to max 512px (the exact Telegram sticker standard).
    3. Run single-threaded ONNX inference without thread lockups.
    """
    t0 = time.time()
    try:
        raw_img = Image.open(io.BytesIO(image_bytes))
        raw_img = ImageOps.exif_transpose(raw_img)
        raw_img = raw_img.convert("RGB")

        # Downscale to max 512px on the longest dimension
        max_dim = max(raw_img.size)
        if max_dim > 512:
            raw_img.thumbnail((512, 512), Image.Resampling.BILINEAR)

        logger.info(f"Image preprocessed for rembg: size={raw_img.size}. Starting model inference...")
        t_model = time.time()

        import rembg
        session = get_session()
        if session:
            out_img = rembg.remove(raw_img, session=session)
        else:
            out_img = rembg.remove(raw_img)

        logger.info(f"rembg model inference finished in {time.time() - t_model:.2f}s (total background removal: {time.time() - t0:.2f}s)")
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
