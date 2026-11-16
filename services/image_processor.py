import io
import os
import asyncio
from typing import Optional, Tuple
from PIL import Image, ImageFilter, ImageDraw, ImageFont

def add_sticker_outline(
    image: Image.Image,
    outline_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    outline_width: int = 10
) -> Image.Image:
    """
    Adds a smooth white sticker outline/border around the alpha silhouette of the image.
    """
    img = image.convert("RGBA")
    alpha = img.getchannel("A")

    # Dilate alpha channel using MaxFilter
    # Kernel size must be odd
    kernel_size = max(3, outline_width * 2 + 1)
    dilated_alpha = alpha.filter(ImageFilter.MaxFilter(kernel_size))

    # Optional: slight blur and threshold for smoother edges
    dilated_alpha = dilated_alpha.filter(ImageFilter.GaussianBlur(1.5))
    dilated_alpha = dilated_alpha.point(lambda p: 255 if p > 100 else 0)

    # Create solid white outline image with dilated alpha
    outline_img = Image.new("RGBA", img.size, outline_color)
    outline_img.putalpha(dilated_alpha)

    # Composite original on top of outline
    return Image.alpha_composite(outline_img, img)

def resize_for_sticker(image: Image.Image, max_size: int = 512) -> Image.Image:
    """
    Resizes image so that one dimension is exactly max_size (512)
    and the other is <= max_size, maintaining aspect ratio.
    """
    img = image.convert("RGBA")
    
    # Auto-crop transparent boundaries if image has alpha
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    w, h = img.size
    if w == 0 or h == 0:
        return img

    ratio = max_size / max(w, h)
    new_w = max(1, int(round(w * ratio)))
    new_h = max(1, int(round(h * ratio)))

    # Force the larger side to be exactly max_size
    if w >= h:
        new_w = max_size
    else:
        new_h = max_size

    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

def get_best_font(size: int = 40) -> ImageFont.ImageFont:
    """Finds a nice bold font for meme/sticker captions."""
    font_candidates = [
        "C:\\Windows\\Fonts\\impact.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def add_text_to_image(
    image: Image.Image,
    text: str,
    position: str = "bottom"  # "top" or "bottom"
) -> Image.Image:
    """
    Adds meme/sticker style text (white with black border) to the image.
    """
    img = image.convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Choose font size dynamically based on image width and text length
    target_width = int(w * 0.9)
    font_size = max(24, int(w / 12))
    font = get_best_font(font_size)

    # Word wrap
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= target_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    # Calculate total height of text block
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1] + 6)

    total_text_h = sum(line_heights)

    # Calculate vertical position with comfortable margins (never touching the edge)
    bottom_margin = max(40, int(h * 0.08))
    top_margin = max(30, int(h * 0.06))

    if position == "top":
        y_cursor = top_margin
    else:  # bottom
        y_cursor = max(10, h - total_text_h - bottom_margin)

    # Draw each line centered with outline
    for idx, line in enumerate(lines):
        line_w = line_widths[idx]
        x = (w - line_w) // 2
        
        # Black stroke outline
        draw.text(
            (x, y_cursor),
            line,
            font=font,
            fill="white",
            stroke_width=max(2, font_size // 10),
            stroke_fill="black"
        )
        y_cursor += line_heights[idx]

    return img

def convert_to_webp(image: Image.Image) -> bytes:
    """Converts PIL Image to WebP bytes suitable for Telegram stickers."""
    output = io.BytesIO()
    image.save(output, format="WEBP", lossless=True, quality=95)
    return output.getvalue()
