"""
题库答题助手 - 主程序
离线运行，截屏圈题 → OCR识别 → 题库搜索 → 弹出答案
"""

import os
import sys
import json
import threading
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# ===== 日志配置 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("AnswerTool")

# ===== 全局常量 =====
APP_NAME = "题库答题助手 v1.0"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
OCR_MODEL_DIR = os.path.join(APP_DIR, "ocr_models")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

os.makedirs(DATA_DIR, exist_ok=True)


class AnswerToolApp:
    """主应用程序"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("480x550")
        self.root.minsize(420, 450)
        self.root.resizable(True, True)

        # 图标（如果有）
        self.root.configure(bg="#F5F5F5")

        # 引擎（延迟初始化）
        self.ocr_engine = None
        self.search_engine = None
        self.github_fetcher = None

        # 状态
        self.is_searching = False

        # 配置
        self.config = self._load_config()

        # 构建界面
        self._setup_styles()
        self._build_ui()

        # 居中窗口
        self._center_window()

        # 加载引擎
        self._init_engines()

        # 加载题库
        self._load_banks()

        # 窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ===== 初始化 =====

    def _setup_styles(self):
        """配置ttk样式"""
        style = ttk.Style()

        # 主题颜色
        self.colors = {
            "primary": "#2563EB",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "bg": "#F8FAFC",
            "card": "#FFFFFF",
        }

        style.configure("Title.TLabel", font=("Microsoft YaHei", 18, "bold"))
        style.configure("Subtitle.TLabel", font=("Microsoft YaHei", 10), foreground="#666666")
        style.configure("Status.TLabel", font=("Microsoft YaHei", 10))
        style.configure("StatusOK.TLabel", font=("Microsoft YaHei", 10), foreground="#10B981")
        style.configure("StatusWarn.TLabel", font=("Microsoft YaHei", 10), foreground="#F59E0B")
        style.configure("BankTitle.TLabel", font=("Microsoft YaHei", 11, "bold"))
        style.configure("BankCount.TLabel", font=("Microsoft YaHei", 9), foreground="#888888")

        # 按钮样式
        style.configure(
            "Capture.TButton",
            font=("Microsoft YaHei", 14, "bold"),
            padding=(30, 12),
        )

    def _build_ui(self):
        """构建主界面"""
        # ===== 标题区域 =====
        title_frame = tk.Frame(self.root, bg="#2563EB", padx=20, pady=15)
        title_frame.pack(fill=tk.X)

        tk.Label(
            title_frame,
            text="📚  题库答题助手",
            font=("Microsoft YaHei", 20, "bold"),
            fg="white",
            bg="#2563EB",
        ).pack(anchor=tk.W)

        tk.Label(
            title_frame,
            text="离线运行 · 截屏圈题 · 自动搜答案",
            font=("Microsoft YaHei", 10),
            fg="#BFDBFE",
            bg="#2563EB",
        ).pack(anchor=tk.W, pady=(2, 0))

        # ===== 题库状态区域 =====
        status_frame = tk.Frame(self.root, bg="#F8FAFC", padx=15, pady=10)
        status_frame.pack(fill=tk.X)

        ttk.Label(status_frame, text="📦 题库状态", style="BankTitle.TLabel").pack(anchor=tk.W)

        # 状态列表容器
        self.status_list_frame = tk.Frame(status_frame, bg="#F8FAFC")
        self.status_list_frame.pack(fill=tk.X, pady=(8, 0))

        # 自定义题库状态
        self.custom_status = self._add_status_row(
            self.status_list_frame, "💾", "自定义题库（RAR/文件）", "未加载", "warn"
        )
        self.textbook1_status = self._add_status_row(
            self.status_list_frame, "📖", "C++ Primer 第5版", "未加载", "warn"
        )
        self.textbook2_status = self._add_status_row(
            self.status_list_frame, "📗", "C++ Primer Plus 第6版", "未加载", "warn"
        )

        # 统计
        self.total_label = ttk.Label(
            status_frame,
            text="题目总数: 0",
            style="Status.TLabel",
        )
        self.total_label.pack(anchor=tk.W, pady=(10, 0))

        # ===== OCR状态 =====
        ocr_frame = tk.Frame(self.root, bg="#F8FAFC", padx=15, pady=8)
        ocr_frame.pack(fill=tk.X)

        self.ocr_status = self._add_status_row(ocr_frame, "🔍", "OCR识别引擎", "加载中...", "warn")

        # ===== 分隔 =====
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=15)

        # ===== 操作按钮区 =====
        btn_frame = tk.Frame(self.root, bg="#F8FAFC", padx=20, pady=20)
        btn_frame.pack(fill=tk.BOTH, expand=True)

        # 圈题按钮（最大的）
        self.capture_btn = tk.Button(
            btn_frame,
            text="🎯  开始圈题\n点击后框选屏幕上的题目",
            font=("Microsoft YaHei", 14, "bold"),
            bg="#2563EB",
            fg="white",
            activebackground="#1D4ED8",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=25,
            pady=15,
            command=self._start_capture,
            borderwidth=0,
        )
        self.capture_btn.pack(fill=tk.X, pady=(0, 12))

        # 辅助按钮行
        aux_frame = tk.Frame(btn_frame, bg="#F8FAFC")
        aux_frame.pack(fill=tk.X)

        self.load_btn = tk.Button(
            aux_frame,
            text="📂 加载题库文件",
            font=("Microsoft YaHei", 10),
            bg="#FFFFFF",
            fg="#333333",
            relief=tk.GROOVE,
            cursor="hand2",
            padx=15,
            pady=8,
            command=self._load_custom_bank,
            borderwidth=1,
        )
        self.load_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.update_btn = tk.Button(
            aux_frame,
            text="🔄 更新教材题库",
            font=("Microsoft YaHei", 10),
            bg="#FFFFFF",
            fg="#333333",
            relief=tk.GROOVE,
            cursor="hand2",
            padx=15,
            pady=8,
            command=self._update_textbooks,
            borderwidth=1,
        )
        self.update_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # ===== 底部状态栏 =====
        status_bar = tk.Frame(self.root, bg="#E5E7EB", height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_text = tk.Label(
            status_bar,
            text="✅ 就绪 — 点击「开始圈题」或按 Ctrl+Shift+Q",
            font=("Microsoft YaHei", 9),
            bg="#E5E7EB",
            fg="#666666",
            anchor=tk.W,
            padx=10,
        )
        self.status_text.pack(fill=tk.X)

        # 快捷键提示
        self.root.bind("<Control-Shift-Q>", lambda e: self._start_capture())
        self.root.bind("<Control-Shift-q>", lambda e: self._start_capture())

    def _add_status_row(self, parent, icon, name, initial_text, initial_style) -> dict:
        """添加一行状态指示"""
        row = tk.Frame(parent, bg="#F8FAFC")
        row.pack(fill=tk.X, pady=2)

        tk.Label(row, text=icon, font=("Microsoft YaHei", 12), bg="#F8FAFC").pack(side=tk.LEFT)

        tk.Label(
            row, text=name,
            font=("Microsoft YaHei", 10),
            bg="#F8FAFC",
            fg="#333333",
        ).pack(side=tk.LEFT, padx=(5, 10))

        status_label = tk.Label(
            row,
            text=initial_text,
            font=("Microsoft YaHei", 9, "bold"),
            bg="#F8FAFC",
        )
        status_label.pack(side=tk.RIGHT)

        # 初始颜色
        if initial_style == "warn":
            status_label.config(fg="#F59E0B")
        elif initial_style == "ok":
            status_label.config(fg="#10B981")
        elif initial_style == "error":
            status_label.config(fg="#EF4444")

        return {
            "row": row,
            "name_label": None,  # 已经直接用了Label
            "status_label": status_label,
        }

    def _center_window(self):
        """居中窗口"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ===== 引擎初始化 =====

    def _init_engines(self):
        """初始化搜索和GitHub引擎"""
        from search_engine import get_search_engine
        self.search_engine = get_search_engine()

        from github_fetcher import GitHubFetcher
        self.github_fetcher = GitHubFetcher(DATA_DIR)

        # OCR在后台初始化
        threading.Thread(target=self._init_ocr, daemon=True).start()

    def _init_ocr(self):
        """后台初始化OCR引擎"""
        try:
            from ocr_engine import get_ocr_engine
            self.ocr_engine = get_ocr_engine(OCR_MODEL_DIR)
            self.ocr_engine._lazy_init()
            self._update_ocr_status("就绪 ✅", "ok")
        except Exception as e:
            logger.error(f"OCR初始化失败: {e}")
            self._update_ocr_status("初始化失败 ❌", "error")

    def _update_ocr_status(self, text, style):
        """更新OCR状态（线程安全）"""
        def _update():
            if hasattr(self, "ocr_status"):
                self.ocr_status["status_label"].config(text=text)
                colors = {"ok": "#10B981", "warn": "#F59E0B", "error": "#EF4444"}
                self.ocr_status["status_label"].config(fg=colors.get(style, "#666666"))
        try:
            self.root.after(0, _update)
        except Exception:
            pass

    # ===== 题库加载 =====

    def _load_banks(self):
        """加载所有题库"""
        # 1. 加载预解析的自定义题库 JSON
        custom_json = os.path.join(DATA_DIR, "custom_parsed.json")
        if os.path.exists(custom_json):
            try:
                import json
                with open(custom_json, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                formatted = []
                for e in entries:
                    formatted.append({
                        "question": e.get("question", ""),
                        "answer": e.get("answer", "(答案见题目)"),
                        "source": f"{e.get('source', '')} > {e.get('chapter', '')} > {e.get('knowledge', '')}",
                    })
                if formatted:
                    self.search_engine.add_bank("C++上机考试题库", formatted)
                    self.custom_status["status_label"].config(
                        text=f"已加载 ✅ ({len(formatted)}题)", fg="#10B981"
                    )
                logger.info(f"自定义题库: {len(formatted)} 题")
            except Exception as e:
                logger.warning(f"加载自定义JSON失败: {e}")

        # 2. 加载GitHub教材（从本地目录解析）
        for dir_name, bank_name, status_row in [
            ("cpp_primer", "C++ Primer 第5版", self.textbook1_status),
            ("cpp_primer_plus", "C++ Primer Plus 第6版", self.textbook2_status),
        ]:
            d = os.path.join(DATA_DIR, dir_name)
            if os.path.isdir(d) and os.listdir(d):
                try:
                    from bank_parser import BankParser
                    parser = BankParser()
                    gh_entries = parser.parse_directory(d, bank_name)
                    if gh_entries:
                        self.search_engine.add_bank(bank_name, gh_entries)
                    status_row["status_label"].config(
                        text=f"已加载 ✅ ({len(gh_entries)}条)", fg="#10B981"
                    )
                    logger.info(f"{bank_name}: {len(gh_entries)} 条")
                except Exception as e:
                    logger.warning(f"解析 {bank_name} 失败: {e}")
                    status_row["status_label"].config(text="解析失败 ❌", fg="#EF4444")
            else:
                status_row["status_label"].config(text="未下载", fg="#F59E0B")

        self._update_total()

    def _load_custom_from_dir(self, dirpath):
        """从目录加载自定义题库"""
        try:
            from bank_parser import BankParser
            parser = BankParser()
            entries = parser.parse_directory(dirpath, "自定义题库")
            if entries:
                self.search_engine.add_bank("自定义题库", entries)
                self.custom_status["status_label"].config(
                    text=f"已加载 ✅ ({len(entries)}题)",
                    fg="#10B981",
                )
                self._update_total()
        except Exception as e:
            logger.error(f"加载自定义题库失败: {e}")

    def _load_custom_bank(self):
        """用户手动加载题库文件/RAR"""
        filepath = filedialog.askopenfilename(
            title="选择题库文件",
            filetypes=[
                ("所有支持的格式", "*.rar;*.zip;*.xlsx;*.xls;*.csv;*.txt;*.json;*.md"),
                ("RAR压缩包", "*.rar"),
                ("Excel表格", "*.xlsx;*.xls"),
                ("CSV文件", "*.csv"),
                ("文本文件", "*.txt"),
                ("Markdown", "*.md"),
                ("JSON文件", "*.json"),
                ("所有文件", "*.*"),
            ],
        )

        if not filepath:
            return

        self._set_status("正在解析题库...", "warn")
        self.load_btn.config(state=tk.DISABLED, text="解析中...")

        def _do_load():
            try:
                ext = Path(filepath).suffix.lower()

                # RAR解压
                if ext == ".rar":
                    entries = self._extract_rar(filepath)
                elif ext == ".zip":
                    entries = self._extract_zip(filepath)
                else:
                    from bank_parser import BankParser
                    parser = BankParser()
                    entries = parser.parse_file(filepath, "自定义题库")

                if entries:
                    self.search_engine.add_bank("自定义题库", entries)
                    self.root.after(0, lambda: self.custom_status["status_label"].config(
                        text=f"已加载 ✅ ({len(entries)}题)", fg="#10B981"
                    ))
                    self.root.after(0, self._update_total)
                    self.root.after(0, lambda: self._set_status(
                        f"✅ 成功加载 {len(entries)} 道题目", "ok"
                    ))
                else:
                    self.root.after(0, lambda: self._set_status(
                        "⚠️ 未能解析出题目，请检查文件格式", "warn"
                    ))

            except Exception as e:
                logger.error(f"加载题库失败: {e}")
                self.root.after(0, lambda: self._set_status(
                    f"❌ 加载失败: {str(e)[:60]}", "error"
                ))
                self.root.after(0, lambda: messagebox.showerror(
                    "加载失败", f"解析题库文件时出错:\n{str(e)[:200]}"
                ))
            finally:
                self.root.after(0, lambda: self.load_btn.config(
                    state=tk.NORMAL, text="📂 加载题库文件"
                ))

        threading.Thread(target=_do_load, daemon=True).start()

    def _extract_rar(self, rar_path: str) -> list:
        """解压RAR并解析"""
        import rarfile
        import tempfile

        temp_dir = tempfile.mkdtemp(prefix="bank_rar_")

        try:
            # 尝试用rarfile解压
            try:
                rf = rarfile.RarFile(rar_path)
                rf.extractall(temp_dir)
            except rarfile.RarCannotExec:
                # 如果没有unrar，尝试用其他方式
                messagebox.showwarning(
                    "需要unrar",
                    "RAR解压需要在同目录下放置 UnRAR.exe\n"
                    "请从 https://www.rarlab.com/rar_add.htm 下载\n\n"
                    "或者：将RAR解压后，直接加载解压出的文件"
                )
                return []

            from bank_parser import BankParser
            parser = BankParser()
            entries = parser.parse_directory(temp_dir, "自定义题库")

            # 复制到data/custom
            custom_dir = os.path.join(DATA_DIR, "custom")
            os.makedirs(custom_dir, exist_ok=True)
            import shutil
            for f in os.listdir(temp_dir):
                src = os.path.join(temp_dir, f)
                dst = os.path.join(custom_dir, f)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)

            return entries

        finally:
            # 清理临时目录
            import shutil
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _extract_zip(self, zip_path: str) -> list:
        """解压ZIP并解析"""
        import zipfile
        import tempfile

        temp_dir = tempfile.mkdtemp(prefix="bank_zip_")

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            from bank_parser import BankParser
            parser = BankParser()
            entries = parser.parse_directory(temp_dir, "自定义题库")

            # 复制到data/custom
            custom_dir = os.path.join(DATA_DIR, "custom")
            os.makedirs(custom_dir, exist_ok=True)
            import shutil
            for f in os.listdir(temp_dir):
                src = os.path.join(temp_dir, f)
                dst = os.path.join(custom_dir, f)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)

            return entries

        finally:
            import shutil
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _update_textbooks(self):
        """从GitHub更新教材题库"""
        if not self.github_fetcher:
            return

        self._set_status("正在从GitHub下载教材题库...", "warn")
        self.update_btn.config(state=tk.DISABLED, text="下载中...")

        def progress_callback(name, status, detail):
            logger.info(f"[{name}] {status}: {detail}")
            self.root.after(0, lambda: self._set_status(
                f"[{name}] {detail}", "warn"
            ))

            if name == "C++ Primer 第5版" and hasattr(self, "textbook1_status"):
                status_text = {"downloading": "下载中...", "extracting": "解压中...",
                               "parsing": "解析中...", "done": "已加载 ✅",
                               "error": "失败 ❌"}
                color = {"done": "#10B981", "error": "#EF4444"}.get(status, "#F59E0B")
                self.root.after(0, lambda: self.textbook1_status["status_label"].config(
                    text=status_text.get(status, status), fg=color
                ))

            if name == "C++ Primer Plus 第6版" and hasattr(self, "textbook2_status"):
                status_text2 = {"downloading": "下载中...", "extracting": "解压中...",
                                "parsing": "解析中...", "done": "已加载 ✅",
                                "error": "失败 ❌"}
                color2 = {"done": "#10B981", "error": "#EF4444"}.get(status, "#F59E0B")
                self.root.after(0, lambda: self.textbook2_status["status_label"].config(
                    text=status_text2.get(status, status), fg=color2
                ))

        def on_complete(results):
            logger.info(f"教材题库更新完成: {list(results.keys())}")
            # 加入搜索引擎
            for name, entries in results.items():
                if entries:
                    self.search_engine.add_bank(name, entries)

            self.root.after(0, self._update_total)
            self.root.after(0, lambda: self._set_status(
                "✅ 教材题库更新完成！", "ok"
            ))
            self.root.after(0, lambda: self.update_btn.config(
                state=tk.NORMAL, text="🔄 更新教材题库"
            ))
            # 如果之前有缓存，合并后的总数
            total = sum(len(e) for e in results.values())
            self.root.after(0, lambda: messagebox.showinfo(
                "更新完成",
                f"教材题库更新完成！\n\n"
                f"共加载 {len(results)} 个题库源，{total} 道题目\n"
                f"已加入搜索引擎，可以开始圈题。"
            ))

        # 异步执行
        self.github_fetcher.fetch_async(
            on_complete=on_complete,
            progress_callback=progress_callback,
        )

    # ===== 截图圈选 → OCR → 搜索 =====

    def _start_capture(self):
        """开始截图圈选流程（主线程执行UI操作）"""
        if self.is_searching:
            return

        if not self.search_engine or self.search_engine.total_entries == 0:
            result = messagebox.askyesno(
                "题库为空",
                "还没有加载任何题库！\n\n"
                "是否现在加载？\n"
                "点击「是」打开文件选择，\n"
                "点击「否」取消。"
            )
            if result:
                self._load_custom_bank()
            return

        self.is_searching = True
        self._set_status("🎯 请用鼠标拖拽框选屏幕上的题目...", "warn")
        self.capture_btn.config(state=tk.DISABLED, text="圈选中...")

        # ===== 阶段1：截图圈选（必须在主线程） =====
        # 最小化主窗口，等待动画完成
        self.root.iconify()
        self.root.update()
        import time
        time.sleep(0.3)

        # 运行圈选覆盖层（阻塞主线程直到完成）
        from capture import CaptureOverlay
        overlay = CaptureOverlay()
        image = overlay.run()

        # 恢复主窗口
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        if image is None:
            self._set_status("已取消圈选", "warn")
            self.capture_btn.config(
                state=tk.NORMAL,
                text="🎯  开始圈题\n点击后框选屏幕上的题目"
            )
            self.is_searching = False
            return

        # ===== 阶段2：OCR + 搜索（后台线程） =====
        self._set_status("🔍 正在识别文字...", "warn")
        self.capture_btn.config(text="识别中...", state=tk.DISABLED)

        threading.Thread(
            target=self._do_ocr_and_search,
            args=(image,),
            daemon=True,
        ).start()

    def _do_ocr_and_search(self, image):
        """OCR识别 + 搜索（后台线程）"""
        try:
            if self.ocr_engine is None:
                self.root.after(0, lambda: messagebox.showerror(
                    "OCR未就绪",
                    "OCR引擎尚未初始化完成，请稍等片刻再试"
                ))
                self.root.after(0, lambda: self._reset_after_search())
                return

            # OCR
            ocr_text = self.ocr_engine.recognize(image)

            if not ocr_text or not ocr_text.strip():
                self.root.after(0, lambda: self._set_status(
                    "⚠️ 未能识别到文字，请重新圈选", "warn"
                ))
                self.root.after(0, lambda: messagebox.showinfo(
                    "未识别到文字",
                    "图片中未识别到文字内容。\n\n"
                    "建议:\n"
                    "1. 确保圈选区域包含完整题目文字\n"
                    "2. 避免圈选过多非文字区域\n"
                    "3. 确保文字清晰可见"
                ))
                self.root.after(0, lambda: self._reset_after_search())
                return

            logger.info(f"OCR结果: {ocr_text[:200]}")

            # 搜索
            self.root.after(0, lambda: self._set_status(
                "🔎 正在搜索答案...", "warn"
            ))

            results = self.search_engine.search(ocr_text, top_k=5, min_score=35)

            # 显示结果（主线程）
            self.root.after(0, lambda: self._show_answer(ocr_text, results))
            self.root.after(0, lambda: self._set_status(
                f"✅ 搜索完成！找到 {len(results)} 个匹配", "ok"
            ))

        except Exception as e:
            logger.exception("搜索流程出错")
            self.root.after(0, lambda: messagebox.showerror(
                "出错", f"搜索过程发生错误:\n{str(e)[:200]}"
            ))
            self.root.after(0, lambda: self._set_status(f"❌ 出错: {e}", "error"))
        finally:
            self.root.after(0, lambda: self._reset_after_search())

    def _reset_after_search(self):
        """搜索完成后恢复按钮状态"""
        self.capture_btn.config(
            state=tk.NORMAL,
            text="🎯  开始圈题\n点击后框选屏幕上的题目"
        )
        self.is_searching = False

    def _show_answer(self, ocr_text, results):
        """弹出答案窗口"""
        from answer_window import show_answer
        show_answer(ocr_text, results, parent=self.root)

    # ===== 辅助方法 =====

    def _update_total(self):
        """更新题目总数"""
        if self.search_engine:
            total = self.search_engine.total_entries
            banks = self.search_engine.bank_names
            self.total_label.config(
                text=f"题目总数: {total} 题  |  题库来源: {len(banks)} 个"
            )

    def _set_status(self, text, level="ok"):
        """设置状态栏文字"""
        colors = {"ok": "#666666", "warn": "#F59E0B", "error": "#EF4444"}
        try:
            self.status_text.config(text=text, fg=colors.get(level, "#666666"))
        except Exception:
            pass

    def _load_config(self):
        """加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self):
        """保存配置"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self):
        """关闭窗口"""
        self._save_config()
        self.root.destroy()

    def run(self):
        """运行应用"""
        self.root.mainloop()


# ===== 入口 =====
def main():
    """程序入口"""
    app = AnswerToolApp()
    app.run()


if __name__ == "__main__":
    main()
