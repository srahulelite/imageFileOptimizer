import os
from PIL import Image

# Quality mapping (0-100)
QUALITY_MAP = {
    "low": 30,
    "avg": 60,
    "high": 85
}

def _is_photographic(img: Image.Image, color_threshold: int = 256) -> bool:
    """
    Heuristic: if number of unique colors > threshold treat as photo-like.
    getcolors(maxcolors) returns None when there are more than maxcolors.
    """
    try:
        # convert to RGBA to count real colors including alpha
        colors = img.convert("RGBA").getcolors(maxcolors=2000000)
        if colors is None:
            return True
        return len(colors) > color_threshold
    except Exception:
        return True

def compress_image_to_path(in_path: str, out_path: str, quality: str = "avg") -> str:
    """
    Compresses image at in_path and writes to out_path (or an appropriate variant).
    Returns the actual path written.

    Strategy:
    - For PNG:
      - If photo-like -> convert to JPEG (lossy) to gain compression.
      - Else (graphics/icons) -> quantize palette and save PNG (lossless-ish but smaller).
    - For JPEG/WebP/others: re-save as JPEG with mapped quality.
    - Always returns the actual output path (caller should use that).
    """
    q = QUALITY_MAP.get(quality, QUALITY_MAP["avg"])
    base_out_dir = os.path.dirname(out_path)
    if base_out_dir and not os.path.exists(base_out_dir):
        os.makedirs(base_out_dir, exist_ok=True)

    try:
        img = Image.open(in_path)
    except Exception as e:
        raise RuntimeError(f"Unable to open image {in_path}: {e}")

    # normalize modes and keep a version without alpha for JPEG conversion
    has_alpha = img.mode in ("RGBA", "LA") or ("transparency" in img.info)
    img_rgb = None
    if has_alpha:
        # composite over white background to preserve visual look when converting to JPEG
        try:
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img)
            img_rgb = bg
        except Exception:
            img_rgb = img.convert("RGB")
    else:
        img_rgb = img.convert("RGB")

    _, in_ext = os.path.splitext(in_path.lower())
    _, out_ext = os.path.splitext(out_path.lower())

    # Handle PNG specially
    if in_ext == ".png":
        is_photo = _is_photographic(img)
        if is_photo:
            # Convert PNG -> JPEG (better for photos). Use .jpg ext for output.
            actual_out_path = os.path.splitext(out_path)[0] + ".jpg"
            try:
                img_rgb.save(actual_out_path, "JPEG", quality=q, optimize=True)
                return actual_out_path
            except Exception as e:
                # fallback: try saving PNG quantized
                try:
                    pal = img.convert("P", palette=Image.ADAPTIVE, colors=128)
                    pal.save(out_path, optimize=True)
                    return out_path
                except Exception as e2:
                    raise RuntimeError(f"Failed to save JPEG or fallback PNG: {e}; {e2}")
        else:
            # Graphic-like PNG: quantize to reduce palette size (keep PNG)
            try:
                pal = img.convert("P", palette=Image.ADAPTIVE, colors=128)
                pal.save(out_path, optimize=True)
                return out_path
            except Exception as e:
                # fallback to RGB JPEG (if quantize fails)
                try:
                    img_rgb.save(os.path.splitext(out_path)[0] + ".jpg", "JPEG", quality=q, optimize=True)
                    return os.path.splitext(out_path)[0] + ".jpg"
                except Exception:
                    raise RuntimeError(f"Failed to save quantized PNG or fallback JPEG: {e}")

    # For JPEG / WEBP / BMP / other formats: write JPEG for consistent compression
    # If caller explicitly asked a .png output, we still prefer saving JPEG for quality mapping,
    # but we will respect out_ext if it's .webp (save webp if pillow supports it).
    try:
        if out_ext in (".webp",):
            # write WEBP (lossy) if user/ caller requested .webp
            img_rgb.save(out_path, "WEBP", quality=q, method=6)
            return out_path
        else:
            # default: save as JPEG
            actual_out = os.path.splitext(out_path)[0] + ".jpg"
            img_rgb.save(actual_out, "JPEG", quality=q, optimize=True)
            return actual_out
    except Exception as e:
        # final fallback: try writing original extension with basic save
        try:
            img.save(out_path)
            return out_path
        except Exception as e2:
            raise RuntimeError(f"Failed to write image to {out_path}: {e}; fallback error: {e2}")
