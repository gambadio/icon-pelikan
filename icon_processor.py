"""
icon_processor.py
Utility helpers for Icon Pelikan (Pillow only, no Qt).
"""

from pathlib import Path
import subprocess
from typing import Tuple, Literal, Union

from PIL import Image, ImageDraw


Shape = Literal["rounded", "circle"]


def create_icon(
    source: Image.Image,
    icon_px: int = 512,
    scale: float = 0.86,
    radius: int = 100,
    shape: Shape = "rounded",
    background: Union[None, Tuple[int, int, int, int]] = None,
) -> Image.Image:
    """
    Returns a Pillow RGBA image with the requested parameters applied.

    • icon_px ........ final square canvas size
    • scale .......... inner image size = icon_px * scale
    • radius ......... corner radius for 'rounded'
    • shape .......... 'rounded' or 'circle'
    • background ..... None  ➜ transparent
                       (r,g,b,a) ➜ solid background colour
    """
    canvas = Image.new("RGBA", (icon_px, icon_px), (0, 0, 0, 0))
    if background is not None:
        bg = Image.new("RGBA", (icon_px, icon_px), background)
        canvas.alpha_composite(bg)

    inner_px = int(icon_px * scale)
    img = source.convert("RGBA").resize((inner_px, inner_px), Image.LANCZOS)

    if shape == "rounded":
        mask = Image.new("L", (inner_px, inner_px), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, inner_px, inner_px), radius=radius, fill=255
        )
    else:  # circle
        mask = Image.new("L", (inner_px, inner_px), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, inner_px, inner_px), fill=255)

    rounded = Image.new("RGBA", (inner_px, inner_px), (0, 0, 0, 0))
    rounded.paste(img, mask=mask)

    # centre
    xy = (icon_px - inner_px) // 2
    canvas.paste(rounded, (xy, xy), rounded)
    return canvas


APPLE_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def export_iconset(img: Image.Image, dest: Path) -> Path:
    """
    Creates an *.iconset* folder in *dest* and fills it with the
    PNGs Apple expects.  Returns the folder path.
    """
    # Use the actual dest folder directly - iconset is already the .iconset directory
    iconset = dest
    iconset.mkdir(parents=True, exist_ok=True)
    for size in APPLE_SIZES:
        p1 = iconset / f"icon_{size}x{size}.png"
        p2 = iconset / f"icon_{size}x{size}@2x.png"
        img.resize((size, size), Image.LANCZOS).save(p1)
        img.resize((size * 2, size * 2), Image.LANCZOS).save(p2)
    return iconset


def to_icns(iconset: Path) -> Path:
    """
    Uses macOS `iconutil` to convert an *.iconset* folder to *.icns*.
    Returns the .icns path. Raises if iconutil is not found.
    """
    icns_path = iconset.with_suffix(".icns")
    try:
        subprocess.run(["iconutil", "-c", "icns", str(iconset)], check=True)
    except subprocess.CalledProcessError as e:
        # Add more descriptive error message
        raise RuntimeError(f"iconutil command failed: {e}. Make sure Xcode Command Line Tools are installed.") from e
    
    # Verify the file was created
    if not icns_path.exists():
        raise FileNotFoundError(f"Expected .icns file was not created at {icns_path}")
    
    return icns_path