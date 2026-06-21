"""
答案显示弹窗
OCR识别 + 搜索完成后弹出，显示匹配结果
"""

import tkinter as tk
from tkinter import ttk


class AnswerWindow:
    """答案展示弹窗"""

    def __init__(self, parent=None):
        self.window = tk.Toplevel(parent)
        self.window.title("📚 答案")
        self.window.geometry("650x500")
        self.window.minsize(500, 350)
        self.window.attributes("-topmost", True)

        # 居中
        self.window.update_idletasks()
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        w, h = 650, 500
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        # 样式
        self._setup_styles()
        self._build_ui()

        # 数据
        self._results = []
        self._current_idx = 0

    def _setup_styles(self):
        """配置ttk样式"""
        style = ttk.Style()

        # 标题标签
        style.configure("Title.TLabel", font=("Microsoft YaHei", 16, "bold"))

        # 匹配分数标签
        style.configure("Score.TLabel", font=("Microsoft YaHei", 11))

        # 来源标签
        style.configure("Source.TLabel", font=("Microsoft YaHei", 9), foreground="#888888")

        # 题目文本
        style.configure("Question.TLabel", font=("Microsoft YaHei", 11), wraplength=580)

        # 答案文本
        style.configure("Answer.TLabel", font=("Microsoft YaHei", 13, "bold"), foreground="#0066CC")

    def _build_ui(self):
        """构建界面"""
        # ===== 顶部 =====
        top_frame = ttk.Frame(self.window, padding=(15, 10))
        top_frame.pack(fill=tk.X)

        self.title_label = ttk.Label(
            top_frame,
            text="🔍 搜索答案",
            style="Title.TLabel"
        )
        self.title_label.pack(side=tk.LEFT)

        self.result_count_label = ttk.Label(
            top_frame,
            text="",
            style="Source.TLabel"
        )
        self.result_count_label.pack(side=tk.RIGHT)

        # 分隔线
        ttk.Separator(self.window, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        # ===== 中间滚动区域 =====
        canvas_frame = ttk.Frame(self.window)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Canvas + Scrollbar
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮滚动
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        # ===== 底部按钮 =====
        ttk.Separator(self.window, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        bottom_frame = ttk.Frame(self.window, padding=(15, 10))
        bottom_frame.pack(fill=tk.X)

        self.copy_btn = ttk.Button(
            bottom_frame,
            text="📋 复制答案",
            command=self._copy_answer,
        )
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.copy_all_btn = ttk.Button(
            bottom_frame,
            text="📋 复制全部",
            command=self._copy_all,
        )
        self.copy_all_btn.pack(side=tk.LEFT)

        self.close_btn = ttk.Button(
            bottom_frame,
            text="关闭",
            command=self.window.destroy,
        )
        self.close_btn.pack(side=tk.RIGHT)

        # ESC关闭
        self.window.bind("<Escape>", lambda e: self.window.destroy())

    def show_results(self, ocr_text: str, results: list):
        """
        显示搜索结果
        Args:
            ocr_text: OCR识别出的原始文本
            results: [{"question": ..., "answer": ..., "score": ..., "bank": ..., "source": ...}, ...]
        """
        self._results = results
        self.ocr_text = ocr_text

        # 清空旧内容
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # 显示OCR识别的文本
        ocr_frame = ttk.LabelFrame(
            self.scroll_frame,
            text="📷 识别到的题目内容",
            padding=(10, 8)
        )
        ocr_frame.pack(fill=tk.X, pady=(0, 10))

        ocr_label = ttk.Label(
            ocr_frame,
            text=ocr_text or "(未能识别到文字)",
            font=("Consolas", 10),
            wraplength=580,
            foreground="#333333",
        )
        ocr_label.pack(anchor=tk.W)

        # 分隔
        ttk.Separator(self.scroll_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        if not results:
            # 无结果
            no_result_frame = ttk.Frame(self.scroll_frame)
            no_result_frame.pack(fill=tk.X, pady=30)

            ttk.Label(
                no_result_frame,
                text="😔 未找到匹配答案",
                font=("Microsoft YaHei", 14),
            ).pack()

            ttk.Label(
                no_result_frame,
                text="请检查:\n"
                     "1. 圈选区域是否包含完整题目文字\n"
                     "2. 题库是否已加载\n"
                     "3. 题目表述是否与题库差异过大",
                font=("Microsoft YaHei", 10),
                foreground="#888888",
                justify=tk.LEFT,
            ).pack(pady=(10, 0))

        else:
            self.result_count_label.config(
                text=f"找到 {len(results)} 个结果"
            )

            # 显示每个结果
            for i, result in enumerate(results):
                card = self._create_result_card(i, result)
                card.pack(fill=tk.X, pady=(0, 10))

            # 如果多结果，显示切换提示
            if len(results) > 1:
                ttk.Label(
                    self.scroll_frame,
                    text=f"共 {len(results)} 个结果，已按匹配度排序",
                    font=("Microsoft YaHei", 9),
                    foreground="#999999",
                ).pack(pady=(0, 10))

        # 更新标题
        if results:
            best = results[0]
            self.title_label.config(
                text=f"✅ 匹配度 {best['score']:.0f}%"
            )

    def _create_result_card(self, index: int, result: dict) -> ttk.Frame:
        """创建单个结果卡片"""
        card = ttk.LabelFrame(
            self.scroll_frame,
            text=f"结果 {index + 1}  |  匹配度: {result['score']:.0f}%  |  来源: {result['bank']}",
            padding=(10, 8),
        )

        # 题目
        q_frame = ttk.Frame(card)
        q_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(
            q_frame,
            text="📝 题库题目:",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(anchor=tk.W)

        q_text = ttk.Label(
            q_frame,
            text=result.get("question", ""),
            wraplength=560,
            font=("Microsoft YaHei", 10),
        )
        q_text.pack(anchor=tk.W, padx=(15, 0))

        # 答案
        a_frame = ttk.Frame(card)
        a_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(
            a_frame,
            text="✅ 答案:",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(anchor=tk.W)

        a_text = tk.Text(
            a_frame,
            height=3,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 12, "bold"),
            fg="#0066CC",
            bg="#F0F8FF",
            relief=tk.FLAT,
            padx=10,
            pady=8,
            borderwidth=1,
        )
        a_text.insert("1.0", result.get("answer", ""))
        a_text.config(state=tk.DISABLED)
        a_text.pack(fill=tk.X, padx=(15, 0))

        # 出处
        source = result.get("source", "")
        if source:
            ttk.Label(
                card,
                text=f"📖 {source}",
                font=("Microsoft YaHei", 8),
                foreground="#AAAAAA",
            ).pack(anchor=tk.W, padx=(15, 0), pady=(5, 0))

        return card

    def _copy_answer(self):
        """复制最佳结果的答案"""
        if not self._results:
            return

        best = self._results[0]
        text = f"题目: {best['question']}\n答案: {best['answer']}"
        self.window.clipboard_clear()
        self.window.clipboard_append(text)
        self.window.update()

        # 提示
        self.copy_btn.config(text="✅ 已复制！")
        self.window.after(2000, lambda: self.copy_btn.config(text="📋 复制答案"))

    def _copy_all(self):
        """复制所有结果"""
        if not self._results:
            return

        lines = []
        for i, r in enumerate(self._results):
            lines.append(f"--- 结果{i+1} (匹配度{r['score']:.0f}%) ---")
            lines.append(f"题目: {r['question']}")
            lines.append(f"答案: {r['answer']}")
            lines.append(f"来源: {r['bank']}")
            lines.append("")

        text = "\n".join(lines)
        self.window.clipboard_clear()
        self.window.clipboard_append(text)

        self.copy_all_btn.config(text="✅ 已复制！")
        self.window.after(2000, lambda: self.copy_all_btn.config(text="📋 复制全部"))

    def show(self):
        """显示窗口"""
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()


def show_answer(ocr_text: str, results: list, parent=None):
    """便捷函数：弹出答案窗口"""
    win = AnswerWindow(parent)
    win.show_results(ocr_text, results)
    return win
