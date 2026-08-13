"""PaddleOCR-VL 识别服务（懒加载；未安装时降级返回提示）。

安装：pip install paddleocr paddlepaddle
新版本用法：PaddleOCR(model_name="PaddleOCR-VL", lang="ch")，调用 .predict(img=bytes)
旧版本用法：PaddleOCR(use_angle_cls=True, lang="ch")，调用 .ocr(img)
下方同时兼容两种调用方式。
"""
import io
from typing import Optional

_ocr = None  # None=未初始化；False=不可用


def _get_ocr():
    global _ocr
    if _ocr is not None:
        return _ocr
    try:
        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(model_name="PaddleOCR-VL", lang="ch")
    except TypeError:
        # 旧版 API
        try:
            from paddleocr import PaddleOCR

            _ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        except Exception:
            _ocr = False
    except Exception:
        _ocr = False
    return _ocr


def recognize(image_bytes: bytes) -> str:
    ocr = _get_ocr()
    if not ocr:
        return "（未安装 paddleocr，OCR 不可用。请执行 pip install paddleocr paddlepaddle 后重试）"
    try:
        result = ocr.predict(img=io.BytesIO(image_bytes))
        lines: list[str] = []
        for page in result:
            for item in page:
                txt = getattr(item, "rec_text", None)
                if txt:
                    lines.append(str(txt))
        return "\n".join(lines) or "（未识别到文本，请换一张更清晰的图片）"
    except AttributeError:
        # 旧版返回结构
        result = ocr.ocr(io.BytesIO(image_bytes), cls=True)
        lines = [line[1][0] for block in result if block for line in block]
        return "\n".join(lines) or "（未识别到文本）"
    except Exception:
        return "（OCR 调用异常，请检查 paddleocr 安装与图片格式）"
