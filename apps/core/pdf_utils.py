"""
Core PDF utilities for Arabic font registration and text shaping.
Works seamlessly across Windows, Linux (PythonAnywhere), and macOS.
"""
import os
from pathlib import Path
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

_ARABIC_FONT_REGISTERED = False
_ARABIC_BOLD_REGISTERED = False

def get_arabic_font_path():
    """
    Search for a valid Arabic TTF font across project static directory,
    system paths (Windows, Linux, macOS).
    """
    candidates = [
        # 1. Project bundled fonts (highest priority, portable)
        settings.BASE_DIR / 'static' / 'fonts' / 'arial.ttf',
        settings.BASE_DIR / 'static' / 'fonts' / 'Cairo-Regular.ttf',
        settings.BASE_DIR / 'static' / 'fonts' / 'Amiri-Regular.ttf',
        # 2. Windows System Fonts
        Path('C:/Windows/Fonts/arial.ttf'),
        Path('C:/Windows/Fonts/tahoma.ttf'),
        Path('C:/Windows/Fonts/segoeui.ttf'),
        # 3. Linux / Debian / Ubuntu / PythonAnywhere Fonts
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'),
        Path('/usr/share/fonts/truetype/freefont/FreeSans.ttf'),
        Path('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'),
    ]
    for path in candidates:
        if path and os.path.exists(str(path)):
            return str(path)
    return None

def get_arabic_bold_font_path():
    """Search for bold Arabic font."""
    candidates = [
        settings.BASE_DIR / 'static' / 'fonts' / 'arialbd.ttf',
        settings.BASE_DIR / 'static' / 'fonts' / 'Cairo-Bold.ttf',
        settings.BASE_DIR / 'static' / 'fonts' / 'Amiri-Bold.ttf',
        Path('C:/Windows/Fonts/arialbd.ttf'),
        Path('C:/Windows/Fonts/tahomabd.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ]
    for path in candidates:
        if path and os.path.exists(str(path)):
            return str(path)
    return get_arabic_font_path()

def register_arabic_fonts():
    """
    Registers 'ArabicFont' and 'ArabicFont-Bold' in ReportLab.
    Returns the font name to use ('ArabicFont' or fallback 'Helvetica').
    """
    global _ARABIC_FONT_REGISTERED, _ARABIC_BOLD_REGISTERED
    if _ARABIC_FONT_REGISTERED:
        return 'ArabicFont'
    
    font_path = get_arabic_font_path()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
            _ARABIC_FONT_REGISTERED = True
            
            bold_path = get_arabic_bold_font_path()
            if bold_path:
                pdfmetrics.registerFont(TTFont('ArabicFont-Bold', bold_path))
                _ARABIC_BOLD_REGISTERED = True
            return 'ArabicFont'
        except Exception as e:
            print(f"Error registering Arabic font from {font_path}: {e}")
            return 'Helvetica'
    return 'Helvetica'

def reshape_arabic(text):
    """
    Reshape and reorder Arabic text for proper RTL display in ReportLab.
    Handles None and non-string types safely.
    """
    if not text:
        return ""
    text_str = str(text).strip()
    if not text_str:
        return ""
    try:
        configuration = {
            'delete_harakat': False,
            'support_ligatures': True,
        }
        reshaped = arabic_reshaper.reshape(text_str, configuration)
        return get_display(reshaped)
    except Exception:
        try:
            return get_display(arabic_reshaper.reshape(text_str))
        except Exception:
            return text_str
