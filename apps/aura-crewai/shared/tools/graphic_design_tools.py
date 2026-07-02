"""
tools/graphic_design_tools.py

Graphic Designer Engine using Python Pillow.
Handles precise text layouts, brand colors, and typography for templates.
"""

import os
import urllib.request
import textwrap
import logging
from typing import Dict, Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("aura.tools.graphic_designer")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Font URLs (Google Fonts TTF links)
FONTS = {
    "Montserrat-Bold": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf",
    "OpenSans-Regular": "https://github.com/google/fonts/raw/main/ofl/opensans/OpenSans-Regular.ttf",
    "OpenSans-Bold": "https://github.com/google/fonts/raw/main/ofl/opensans/OpenSans-Bold.ttf",
}

def _get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Download the font if it doesn't exist, then load it."""
    font_path = os.path.join(ASSETS_DIR, f"{name}.ttf")
    if not os.path.exists(font_path):
        url = FONTS.get(name)
        if url:
            try:
                logger.info(f"Downloading font {name}...")
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                logger.error(f"Failed to download font {name}: {e}")
                # Fallback to default load which might throw exception, but we try
        else:
            logger.warning(f"Font {name} not found in repository URLs.")

    try:
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        logger.error(f"Error loading font {font_path}: {e}")
        return ImageFont.load_default()

def generate_sakluma_yellow(text: str) -> Dict[str, Any]:
    """Generate the SaklumaYellow template image with the provided text.
    
    Args:
        text: The headline or quote to place in the center of the image.
    """
    try:
        width, height = 1080, 1080
        background_color = "#eeb822" # Mustard Yellow
        
        # 1. Create Canvas
        img = Image.new("RGB", (width, height), color=background_color)
        draw = ImageDraw.Draw(img)
        
        # 2. Load Fonts
        font_main = _get_font("Montserrat-Bold", 72)
        font_footer = _get_font("OpenSans-Regular", 30)
        font_footer_bold = _get_font("OpenSans-Bold", 30)
        
        # 3. Word Wrap and Centering Main Text
        # Max chars per line approx based on size 72 in 1080px is around 20-25
        margin = 100
        max_width = width - (margin * 2)
        
        # Simple word wrap
        wrapped_text = textwrap.fill(text, width=25)
        
        # Calculate bounding box for text to center it
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font_main, align="center")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        draw.multiline_text((x, y), wrapped_text, font=font_main, fill="white", align="center")
        
        # 4. Draw Footer
        footer_x = 50
        footer_y = height - 100
        
        footer_line1 = "For more information :"
        footer_line2 = "www.saklomak.my"
        
        draw.text((footer_x, footer_y), footer_line1, font=font_footer, fill="white")
        draw.text((footer_x, footer_y + 40), footer_line2, font=font_footer_bold, fill="white")
        
        # 5. Save and return path
        output_dir = os.path.join(os.path.dirname(__file__), "..", "public", "generated")
        os.makedirs(output_dir, exist_ok=True)
        
        import uuid
        filename = f"sakluma_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(output_dir, filename)
        
        img.save(filepath, "JPEG", quality=95)
        
        return {
            "status": "success",
            "message": "Grafik SaklumaYellow berjaya dijana.",
            "filepath": filepath,
            "filename": filename
        }
        
    except Exception as e:
        logger.error(f"Error generating SaklumaYellow graphic: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
