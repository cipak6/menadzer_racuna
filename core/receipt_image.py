"""
Renders the plain text receipt from purs.gov.rs into a PNG image.
"""

import os
from datetime import datetime
from pathlib import Path
import sys


def render_receipt_image(pre_text: str, save_dir: str, filename_prefix: str = 'receipt') -> str:
    """
    Renders the <pre> receipt text into a PNG and saves it.
    Returns the path to the saved image.
    """
    from PIL import Image, ImageDraw, ImageFont

    lines = pre_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    lines = [l for l in lines if 'KRAJ FISKALNOG' not in l.upper() and 'КРАЈ ФИСКАЛНОГ' not in l.upper()]
    # Try to find a monospaced font
    font = None
    font_size = 14
    import sys
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [
        os.path.join(base, 'assets', 'DejaVuSansMono.ttf'),
        # Windows fallback
        'C:/Windows/Fonts/arial.ttf',
        # Mac fallback
        '/System/Library/Fonts/Supplemental/Arial.ttf',
    ]


    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()

    # Measure dimensions
    padding = 20
    dummy = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy)
    line_height = font_size + 4
    max_width = max((draw.textlength(line, font=font) for line in lines), default=400)
    width = int(max_width * 1.05) + padding * 2  # 5% buffer for rendering differences
    height = line_height * len(lines) + padding * 2

    # Draw
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    y = padding
    for line in lines:
        draw.text((padding, y), line, fill='black', font=font)
        y += line_height

    # Save
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    filename = f"{filename_prefix}.png"
    full_path = save_path / filename
    img.save(str(full_path))
    return str(full_path)

def add_qr_to_receipt(receipt_image_path: str, url: str) -> str:
    """
    Adds a QR code of the invoice URL to the bottom of the receipt image.
    Overwrites the file in place and returns the path.
    """
    import qrcode
    from PIL import Image

    # Generate QR code
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='black', back_color='white').convert('RGB')

    # Load receipt
    receipt = Image.open(receipt_image_path)
    rw, rh = receipt.size
    qw, qh = qr_img.size

    # Scale QR to fit receipt width with padding
    target_qr_width = min(rw - 40, 300)
    scale = target_qr_width / qw
    qr_img = qr_img.resize((int(qw * scale), int(qh * scale)), Image.NEAREST)
    qw, qh = qr_img.size

    # Add label
    from PIL import ImageDraw, ImageFont
    label_height = 30
    combined_height = rh + qh + label_height + 40
    combined = Image.new('RGB', (rw, combined_height), color='white')
    combined.paste(receipt, (0, 0))

    # Draw separator line
    draw = ImageDraw.Draw(combined)
    separator_y = rh + 10
    draw.line([(20, separator_y), (rw - 20, separator_y)], fill='#CCCCCC', width=1)

    # Paste QR centered
    qr_x = (rw - qw) // 2
    qr_y = separator_y + 10
    combined.paste(qr_img, (qr_x, qr_y))

    # Label below QR
    try:
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        font_path = os.path.join(base, 'assets', 'DejaVuSansMono.ttf')
        if not os.path.exists(font_path):
            raise FileNotFoundError
        font = ImageFont.truetype(font_path, 13)
    except Exception:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(combined)
    label = '======== KRAJ FISKALNOG RACUNA ========'
    label_w = draw.textlength(label, font=font)
    label_y = qr_y + qh + 10
    draw.text(((rw - label_w) // 2, label_y), label, fill='black', font=font)

    combined_height = label_y + 30
    combined = combined.crop((0, 0, rw, combined_height))

    combined.save(receipt_image_path)
    return receipt_image_path