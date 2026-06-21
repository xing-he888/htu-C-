"""
OCR 识别引擎 - 基于 EasyOCR
完全离线运行，模型文件存储在程序目录下的 ocr_models/
"""
import os
import logging

logger = logging.getLogger(__name__)


class OCREngine:
    """离线OCR引擎，识别截图中的中文/英文/代码"""

    def __init__(self, model_dir: str = None):
        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "ocr_models"
            )
        os.makedirs(model_dir, exist_ok=True)
        self.model_dir = model_dir
        self._reader = None
        self._initialized = False

    def _lazy_init(self):
        """延迟初始化，首次使用时才加载模型"""
        if self._initialized:
            return

        logger.info("正在加载 EasyOCR 模型（首次需下载，约1-2分钟）...")

        try:
            import easyocr
            self._reader = easyocr.Reader(
                ["ch_sim", "en"],
                model_storage_directory=self.model_dir,
                gpu=False,
                verbose=False,
            )
            self._initialized = True
            logger.info("EasyOCR 模型加载完成！")
        except Exception as e:
            logger.error(f"OCR模型加载失败: {e}")
            raise RuntimeError(
                f"OCR引擎初始化失败: {e}\n"
                "请确保网络畅通（首次需下载模型到 ocr_models/）"
            )

    def recognize(self, image) -> str:
        """
        识别图片中的文字
        Args:
            image: PIL Image 对象 或 numpy array
        Returns:
            识别出的完整文本
        """
        self._lazy_init()

        import numpy as np
        from PIL import Image

        if isinstance(image, Image.Image):
            img_array = np.array(image)
        else:
            img_array = image

        try:
            results = self._reader.readtext(img_array)
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return ""

        if not results:
            return ""

        # EasyOCR 返回 [(bbox, text, confidence), ...]
        # 按垂直坐标排序，模拟自上而下的阅读顺序
        def get_y_center(item):
            bbox = item[0]
            if bbox is not None and len(bbox) >= 4:
                y_coords = [p[1] for p in bbox if len(p) >= 2]
                return sum(y_coords) / len(y_coords)
            return 0

        sorted_results = sorted(results, key=get_y_center)

        lines = []
        for bbox, text, confidence in sorted_results:
            if confidence > 0.3:
                lines.append(text)

        return "\n".join(lines)

    @property
    def is_ready(self) -> bool:
        try:
            self._lazy_init()
            return True
        except Exception:
            return False


_ocr_instance = None


def get_ocr_engine(model_dir: str = None) -> OCREngine:
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = OCREngine(model_dir)
    return _ocr_instance
