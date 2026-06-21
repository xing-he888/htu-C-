"""
屏幕圈选模块
全屏半透明遮罩 + 鼠标拖拽框选 → 截图
"""

import tkinter as tk
from PIL import ImageGrab, Image, ImageEnhance
import logging

logger = logging.getLogger(__name__)


class CaptureOverlay:
    """
    全屏截图圈选窗口
    使用方式:
        overlay = CaptureOverlay()
        image = overlay.run()  # 阻塞直到用户完成圈选，返回PIL Image
    """

    def __init__(self):
        self.root = tk.Toplevel()
        self.root.title("")

        # 全屏
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        self.root.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.35)  # 半透明

        # 去掉窗口装饰
        self.root.overrideredirect(True)

        # 先截取整个屏幕作为背景
        self.full_screenshot = ImageGrab.grab(
            bbox=(0, 0, self.screen_w, self.screen_h)
        )
        # 调暗作为遮罩背景
        enhancer = ImageEnhance.Brightness(self.full_screenshot)
        self._bg_image_tk = None  # 保持引用

        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_w,
            height=self.screen_h,
            highlightthickness=0,
            cursor="cross",
            bg="black",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 状态
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.result_image = None
        self._done = False

        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # 按ESC取消
        self.root.bind("<Escape>", self._on_cancel)
        self.root.bind("<Key>", lambda e: None)  # 拦截所有键盘事件

        # 提示文字
        self.hint_text = self.canvas.create_text(
            self.screen_w // 2,
            self.screen_h - 60,
            text="🖱 按住鼠标左键拖拽框选题目区域  |  按 ESC 取消",
            fill="#00FF88",
            font=("Microsoft YaHei", 14, "bold"),
        )

    def run(self) -> Image.Image:
        """
        运行圈选窗口（阻塞直到完成）
        Returns:
            PIL Image 或 None（用户取消时）
        """
        self.result_image = None
        self._done = False

        # 显示窗口
        self.root.deiconify()
        self.root.focus_force()
        self.root.grab_set()  # 模态

        # 等待用户完成
        self.root.wait_window()

        return self.result_image

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

        if self.current_rect:
            self.canvas.delete(self.current_rect)
        if hasattr(self, "hint_text"):
            self.canvas.delete(self.hint_text)

        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            event.x, event.y,
            outline="#00FF00",
            width=2,
            dash=(8, 4),
        )

        # 圈选区域的亮度预览（挖空效果）
        self._update_highlight(event.x, event.y)

    def _on_drag(self, event):
        if self.current_rect:
            self.canvas.coords(
                self.current_rect,
                self.start_x, self.start_y,
                event.x, event.y
            )
            self._update_highlight(event.x, event.y)

    def _on_release(self, event):
        """松手 → 截图选中区域"""
        if not self.start_x:
            return

        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        # 最小区域检查
        if x2 - x1 < 20 or y2 - y1 < 20:
            logger.warning("圈选区域太小")
            # 重置，让用户重新选
            self.start_x = None
            self.start_y = None
            return

        # 截图
        try:
            self.result_image = self.full_screenshot.crop((x1, y1, x2, y2))
            logger.info(f"截图成功: {x2-x1}x{y2-y1}")
        except Exception as e:
            logger.error(f"截图失败: {e}")
            self.result_image = None

        self._done = True
        self.root.grab_release()
        self.root.destroy()

    def _on_cancel(self, event=None):
        """ESC取消"""
        self.result_image = None
        self._done = True
        self.root.grab_release()
        self.root.destroy()

    def _update_highlight(self, x, y):
        """更新选择的亮度高亮"""
        pass  # 简化实现，只用矩形框表示


class CaptureTool:
    """
    截图圈选工具（便捷封装）
    自动处理主窗口最小化 → 截图 → 恢复
    """

    def __init__(self, main_window: tk.Tk = None):
        self.main_window = main_window

    def capture(self) -> Image.Image:
        """
        执行一次截图圈选
        1. 最小化主窗口
        2. 显示圈选覆盖层
        3. 用户圈选完成
        4. 恢复主窗口
        """
        # 隐藏主窗口
        if self.main_window:
            self.main_window.iconify()
            # 等窗口最小化
            self.main_window.update()
            self.main_window.after(300)

        # 进行圈选
        overlay = CaptureOverlay()
        image = overlay.run()

        # 恢复主窗口
        if self.main_window:
            self.main_window.deiconify()
            self.main_window.lift()
            self.main_window.focus_force()

        return image


# ===== 测试 =====
if __name__ == "__main__":
    root = tk.Tk()
    root.title("测试 - 截图圈选")
    root.geometry("300x200")

    def test_capture():
        tool = CaptureTool(root)
        img = tool.capture()
        if img:
            img.show()
            print(f"截图大小: {img.size}")
        else:
            print("用户取消了截图")

    btn = tk.Button(root, text="测试圈选", command=test_capture, font=("Microsoft YaHei", 14))
    btn.pack(pady=40)

    root.mainloop()
