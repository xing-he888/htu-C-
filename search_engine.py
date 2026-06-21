"""
搜索匹配引擎 - 基于 rapidfuzz 的高速模糊匹配
搜索策略：精准匹配 > 子串匹配 > 模糊匹配
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SearchEngine:
    """题库搜索引擎"""

    def __init__(self):
        self._banks = {}       # {"bank_name": [entries]}
        self._all_entries = []  # 扁平化后的全部条目列表
        self._dirty = False

    def add_bank(self, name: str, entries: list):
        """
        添加一个题库
        Args:
            name: 题库名称（如 "自定义题库"、"C++ Primer 第5版"）
            entries: [{"question": str, "answer": str, "source": str}, ...]
        """
        if not entries:
            logger.warning(f"题库 '{name}' 为空，跳过")
            return

        self._banks[name] = entries
        self._dirty = True
        logger.info(f"题库 '{name}' 已加载，共 {len(entries)} 条")

    def remove_bank(self, name: str):
        """移除题库"""
        if name in self._banks:
            del self._banks[name]
            self._dirty = True

    def _rebuild_index(self):
        """重建搜索索引"""
        self._all_entries = []
        for bank_name, entries in self._banks.items():
            for entry in entries:
                self._all_entries.append({
                    **entry,
                    "_bank": bank_name
                })
        self._dirty = False
        logger.info(f"搜索索引已重建，总题目数: {len(self._all_entries)}")

    def search(self, query: str, top_k: int = 5, min_score: float = 40.0) -> list:
        """
        搜索答案
        Args:
            query: OCR识别出的题目文本
            top_k: 返回前K个结果
            min_score: 最低匹配分数阈值（0-100）
        Returns:
            [{"question": ..., "answer": ..., "score": ..., "bank": ..., "source": ...}, ...]
        """
        if self._dirty:
            self._rebuild_index()

        if not query or not self._all_entries:
            return []

        # 清洗查询文本
        query_clean = self._clean_text(query)

        from rapidfuzz import fuzz, process

        # 准备候选题目文本
        candidates = []
        for entry in self._all_entries:
            q_text = self._clean_text(entry["question"])
            candidates.append(q_text)

        # 使用 rapidfuzz 批量计算相似度
        results = []
        for i, entry in enumerate(self._all_entries):
            q_text = candidates[i]

            # 多种匹配策略加权
            score_partial = fuzz.partial_ratio(query_clean, q_text)      # 部分匹配
            score_token = fuzz.token_sort_ratio(query_clean, q_text)     # 词序不敏感
            score_ratio = fuzz.ratio(query_clean, q_text)                # 完全匹配

            # 综合评分
            score = max(
                score_partial * 0.5 + score_token * 0.3 + score_ratio * 0.2,
                score_partial,  # 部分匹配有时单独就很准
            )

            if score >= min_score:
                results.append({
                    "question": entry["question"],
                    "answer": entry["answer"],
                    "score": round(score, 1),
                    "bank": entry.get("_bank", "未知"),
                    "source": entry.get("source", ""),
                })

        # 按分数降序
        results.sort(key=lambda x: x["score"], reverse=True)

        # 去重（相同的question+answer只保留分数最高的）
        seen = set()
        unique_results = []
        for r in results:
            key = (r["question"][:80], r["answer"][:80])
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        return unique_results[:top_k]

    def _clean_text(self, text: str) -> str:
        """清洗文本，用于匹配"""
        if not text:
            return ""
        # 移除多余空白
        text = re.sub(r"\s+", " ", text)
        # 移除特殊字符（保留中文、英文、数字、运算符）
        text = re.sub(r"[^\w一-鿿+\-*/=<>!&|.(),;:\[\]{}#@$%]+", "", text)
        return text.strip().lower()

    @property
    def total_entries(self) -> int:
        return sum(len(e) for e in self._banks.values())

    @property
    def bank_names(self) -> list:
        return list(self._banks.keys())

    def bank_stats(self) -> dict:
        return {name: len(entries) for name, entries in self._banks.items()}


# 全局单例
_search_engine = None


def get_search_engine() -> SearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine
