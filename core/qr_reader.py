"""
Extracts purs.gov.rs URL from a photo of an invoice by decoding the QR code.
Requires: pyzbar, Pillow, opencv-python
"""
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import os
import sys
if sys.platform == 'win32':
    if getattr(sys, 'frozen', False):
        os.add_dll_directory(sys._MEIPASS)

def decode_qr_from_image(image_path: str) -> str | None:
    Image.MAX_IMAGE_PIXELS = None

    try:
        import zxingcpp
        img = Image.open(image_path)
        
        results = zxingcpp.read_barcodes(img)
        for r in results:
            if 'purs.gov.rs' in r.text or 'suf.' in r.text:
                return r.text
        
        max_dim = 3000
        if img.width > max_dim or img.height > max_dim:
            ratio = max_dim / max(img.width, img.height)
            small = img.resize((int(img.width * ratio), int(img.height * ratio)))
            results = zxingcpp.read_barcodes(small)
            for r in results:
                if 'purs.gov.rs' in r.text or 'suf.' in r.text:
                    return r.text
    except Exception:
        pass

    try:
        from pyzbar.pyzbar import decode
        img = Image.open(image_path)
        codes = decode(img)
        for code in codes:
            data = code.data.decode('utf-8')
            if 'purs.gov.rs' in data or 'suf.' in data:
                return data
    except Exception:
        pass

    return None

def extract_url_from_file(file_path: str) -> str:
    if not file_path:
        raise ValueError("No file path provided.")
    if file_path.lower().endswith('.pdf'):
        return extract_url_from_pdf(file_path)
    return decode_qr_from_image(file_path)


def extract_url_from_pdf(pdf_path: str) -> str:
    Image.MAX_IMAGE_PIXELS = None
    try:
        import fitz
    except ImportError:
        raise ImportError("Install pymupdf: pip install pymupdf")

    doc = fitz.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")

        try:
            import zxingcpp
            from PIL import ImageEnhance, ImageFilter
            import io
            img = Image.open(io.BytesIO(img_bytes))
            # Try original first
            results = zxingcpp.read_barcodes(img)
            for r in results:
                if 'purs.gov.rs' in r.text or 'suf.' in r.text:
                    return r.text
            # Try with sharpening and contrast boost
            img2 = img.filter(ImageFilter.SHARPEN)
            img2 = ImageEnhance.Contrast(img2).enhance(2.0)
            results = zxingcpp.read_barcodes(img2)
            for r in results:
                if 'purs.gov.rs' in r.text or 'suf.' in r.text:
                    return r.text
        except Exception as e:
            print(f"zxingcpp error: {e}")

        try:
            from pyzbar.pyzbar import decode
            import io
            codes = decode(Image.open(io.BytesIO(img_bytes)))
            for code in codes:
                data = code.data.decode('utf-8')
                if 'purs.gov.rs' in data or 'suf.' in data:
                    return data
        except Exception:
            pass

    raise ValueError("No Serbian fiscal QR code found in PDF.")
