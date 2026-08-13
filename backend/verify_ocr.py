"""安装完成后验证 OCR 是否可用：生成一张含中文文字的测试图，调用 ocr_service 识别。
用法（在 backend venv 中）：
    .venv/Scripts/python.exe verify_ocr.py
"""
import io
from PIL import Image, ImageDraw, ImageFont

from app.services import ocr_service


def make_test_image() -> bytes:
    img = Image.new("RGB", (480, 160), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 28)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 30), "错题本 OCR 识别测试", fill="black", font=font)
    draw.text((20, 80), "f(x)=x^2+1", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    data = make_test_image()
    text = ocr_service.recognize(data)
    print("=== OCR 识别结果 ===")
    print(text)
    print("=== 是否可用 ===", "可用" if "未安装" not in text and "不可用" not in text else "不可用")
