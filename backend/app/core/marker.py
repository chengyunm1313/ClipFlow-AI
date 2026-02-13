"""
ClipFlow AI — 標記詞偵測模組
從逐字稿中比對 NG/OK/START/END 關鍵字
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher

from app.models.schemas import (
    Marker,
    MarkerType,
    TranscriptSegment,
    TranscriptWord,
)

logger = logging.getLogger(__name__)

# 模糊比對的最低相似度門檻
FUZZY_THRESHOLD = 0.75


def _fuzzy_match(text: str, keyword: str) -> float:
    """
    計算文字與關鍵字的相似度

    Args:
        text: 待比對的文字
        keyword: 關鍵字

    Returns:
        相似度 (0.0 ~ 1.0)
    """
    text = text.strip().lower()
    keyword = keyword.strip().lower()

    # 完全匹配
    if text == keyword or keyword in text:
        return 1.0

    # 模糊比對
    return SequenceMatcher(None, text, keyword).ratio()


def _check_word_sequence(
    words: list[TranscriptWord],
    start_idx: int,
    keyword: str,
) -> tuple[bool, int, float]:
    """
    檢查從 start_idx 開始的連續詞語是否匹配多字關鍵字

    Returns:
        (是否匹配, 結束索引, 相似度)
    """
    # 單字關鍵字
    if len(keyword) <= 3:
        score = _fuzzy_match(words[start_idx].word, keyword)
        return score >= FUZZY_THRESHOLD, start_idx, score

    # 多字關鍵字：嘗試拼接連續 1~5 個詞
    for span in range(1, min(6, len(words) - start_idx + 1)):
        combined = "".join(
            words[start_idx + j].word for j in range(span)
        )
        score = _fuzzy_match(combined, keyword)
        if score >= FUZZY_THRESHOLD:
            return True, start_idx + span - 1, score

    return False, start_idx, 0.0


def detect_markers(
    transcript: list[TranscriptSegment],
    ng_keywords: list[str],
    ok_keywords: list[str],
    start_keywords: list[str] | None = None,
    end_keywords: list[str] | None = None,
) -> list[Marker]:
    """
    從逐字稿中偵測語音標記

    Args:
        transcript: 逐字稿段落列表
        ng_keywords: NG 標記關鍵字
        ok_keywords: OK 標記關鍵字
        start_keywords: 區間開始關鍵字（區間法用）
        end_keywords: 區間結束關鍵字（區間法用）

    Returns:
        偵測到的 Marker 列表（按時間排序）
    """
    start_keywords = start_keywords or []
    end_keywords = end_keywords or []

    markers: list[Marker] = []

    # 建立 (關鍵字, 類型) 的映射
    keyword_map: list[tuple[str, MarkerType]] = []
    for kw in ng_keywords:
        keyword_map.append((kw, MarkerType.NG))
    for kw in ok_keywords:
        keyword_map.append((kw, MarkerType.OK))
    for kw in start_keywords:
        keyword_map.append((kw, MarkerType.START))
    for kw in end_keywords:
        keyword_map.append((kw, MarkerType.END))

    # 先嘗試整句級別匹配（對於短標記詞效果更好）
    for seg in transcript:
        seg_text = seg.text.strip()
        for keyword, mtype in keyword_map:
            score = _fuzzy_match(seg_text, keyword)
            if score >= FUZZY_THRESHOLD:
                markers.append(
                    Marker(
                        type=mtype,
                        word=seg_text,
                        start=seg.start,
                        end=seg.end,
                        confidence=round(score, 3),
                    )
                )
                break  # 每個段落只匹配一次

    # 再做逐詞級別匹配（捕捉段落中間的標記詞）
    for seg in transcript:
        if not seg.words:
            continue

        i = 0
        while i < len(seg.words):
            word = seg.words[i]
            matched = False

            for keyword, mtype in keyword_map:
                is_match, end_idx, score = _check_word_sequence(
                    seg.words, i, keyword
                )
                if is_match:
                    # 避免重複（檢查是否已在段落級別匹配過）
                    end_word = seg.words[end_idx]
                    already_found = any(
                        abs(m.start - word.start) < 0.1
                        and abs(m.end - end_word.end) < 0.1
                        for m in markers
                    )
                    if not already_found:
                        markers.append(
                            Marker(
                                type=mtype,
                                word="".join(
                                    seg.words[j].word
                                    for j in range(i, end_idx + 1)
                                ),
                                start=word.start,
                                end=end_word.end,
                                confidence=round(score, 3),
                            )
                        )
                    i = end_idx + 1
                    matched = True
                    break

            if not matched:
                i += 1

    # 依時間排序
    markers.sort(key=lambda m: m.start)

    logger.info("偵測到 %d 個標記", len(markers))
    for m in markers:
        logger.debug(
            "  [%s] %.2f-%.2f '%s' (信心度=%.2f)",
            m.type.value, m.start, m.end, m.word, m.confidence,
        )

    return markers
