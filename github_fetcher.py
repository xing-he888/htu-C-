"""
GitHub 教材拉取器
自动从 GitHub 下载 C++ Primer 和 C++ Primer Plus 的习题仓库
"""

import os
import io
import json
import zipfile
import shutil
import logging
import threading

logger = logging.getLogger(__name__)

# 两本常用C++教材的GitHub仓库
TEXTBOOK_REPOS = [
    {
        "name": "C++ Primer 第5版",
        "dir": "cpp_primer",
        "repo": "applenob/Cpp_Primer_Practice",
        "branch": "master",
        "url": "https://api.github.com/repos/applenob/Cpp_Primer_Practice/zipball/master",
    },
    {
        "name": "C++ Primer Plus 第6版",
        "dir": "cpp_primer_plus",
        "repo": "FengYeMo/Cpp-Primer-Plus-6th-learn",
        "branch": "master",
        "url": "https://api.github.com/repos/FengYeMo/Cpp-Primer-Plus-6th-learn/zipball/master",
    },
]


class GitHubFetcher:
    """从GitHub拉取教材习题仓库"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        # 缓存索引文件
        self._cache_file = os.path.join(data_dir, "_bank_cache.json")

    def fetch_all(self, progress_callback=None) -> dict:
        """
        拉取全部教材仓库
        Args:
            progress_callback: 进度回调 callback(name, status, detail)
        Returns:
            {"C++ Primer 第5版": [entries], ...}
        """
        import requests

        results = {}

        for i, repo_info in enumerate(TEXTBOOK_REPOS):
            name = repo_info["name"]
            repo_dir = os.path.join(self.data_dir, repo_info["dir"])

            if progress_callback:
                progress_callback(name, "downloading", f"正在从GitHub下载...")

            try:
                # 下载ZIP
                resp = requests.get(
                    repo_info["url"],
                    timeout=120,
                    headers={"User-Agent": "AnswerTool/1.0"},
                    allow_redirects=True,
                )
                resp.raise_for_status()

                if progress_callback:
                    progress_callback(name, "extracting", "正在解压...")

                # 解压到目标目录
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir)
                os.makedirs(repo_dir, exist_ok=True)

                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    # GitHub ZIP内部有一个顶层目录，去掉它
                    root_dir = zf.namelist()[0].split("/")[0]
                    for member in zf.namelist():
                        if member.startswith(f"{root_dir}/") and len(member) > len(root_dir) + 1:
                            rel_path = member[len(root_dir) + 1:]
                            target_path = os.path.join(repo_dir, rel_path)
                            if member.endswith("/"):
                                os.makedirs(target_path, exist_ok=True)
                            else:
                                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                                with zf.open(member) as src, open(target_path, "wb") as dst:
                                    dst.write(src.read())

                if progress_callback:
                    progress_callback(name, "parsing", "正在解析题库...")

                # 解析仓库中的题目
                from bank_parser import BankParser
                parser = BankParser()
                entries = parser.parse_directory(repo_dir, name)
                results[name] = entries

                if progress_callback:
                    progress_callback(name, "done", f"完成！共 {len(entries)} 条题目")

            except requests.exceptions.ConnectionError:
                if progress_callback:
                    progress_callback(name, "error", "网络连接失败，请检查网络")
                logger.error(f"下载 {name} 失败: 网络连接错误")
            except requests.exceptions.Timeout:
                if progress_callback:
                    progress_callback(name, "error", "下载超时")
                logger.error(f"下载 {name} 超时")
            except Exception as e:
                if progress_callback:
                    progress_callback(name, "error", str(e)[:50])
                logger.error(f"处理 {name} 失败: {e}")

        return results

    def fetch_async(self, on_complete=None, progress_callback=None):
        """
        异步拉取（在后台线程中执行）
        """
        def _run():
            results = self.fetch_all(progress_callback=progress_callback)
            # 缓存结果
            self._save_cache(results)
            if on_complete:
                on_complete(results)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def load_cached(self) -> dict:
        """加载缓存的题库"""
        if not os.path.exists(self._cache_file):
            return {}

        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self, results: dict):
        """缓存解析结果"""
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")

    @property
    def has_cache(self) -> bool:
        return os.path.exists(self._cache_file)

    def get_data_dirs(self) -> list:
        """获取已有的教材目录列表"""
        dirs = []
        for repo_info in TEXTBOOK_REPOS:
            d = os.path.join(self.data_dir, repo_info["dir"])
            if os.path.isdir(d) and os.listdir(d):
                dirs.append(d)
        return dirs
