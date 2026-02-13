"""
ClipFlow AI — 片段切片模組
根據標記結果，以回溯法或區間法產生保留/捨棄片段
"""

from __future__ import annotations

import logging
from app.models.schemas import Marker, MarkerType, Segment, TranscriptSegment

logger = logging.getLogger(__name__)


def slice_backtrack(
    markers: list[Marker],
    transcript: list[TranscriptSegment],
    total_duration: float,
    pre_buffer: float = 0.5,
    post_buffer: float = 0.3,
) -> list[Segment]:
    """
    回溯法切片：聽到 OK 標記時，保留從上一個 NG 標記（或靜音區間）
    之後到 OK 標記之前的內容。

    邏輯：
    1. 找到每個 OK 標記
    2. 往前搜尋最近的 NG 標記
    3. 保留 NG 結束 ~ OK 開始 的區間

    Args:
        markers: 偵測到的標記列表
        transcript: 逐字稿
        total_duration: 影片總時長
        pre_buffer: 切點前緩衝（秒）
        post_buffer: 切點後緩衝（秒）

    Returns:
        切片結果列表
    """
    segments: list[Segment] = []

    # 分離 OK 和 NG 標記
    ok_markers = [m for m in markers if m.type == MarkerType.OK]
    ng_markers = [m for m in markers if m.type == MarkerType.NG]

    if not ok_markers:
        logger.warning("未偵測到 OK 標記，無法進行回溯法切片")
        # 若無標記，將整段視為保留
        if total_duration > 0:
            segments.append(
                Segment(start=0.0, end=total_duration, type="keep")
            )
        return segments

    for ok in ok_markers:
        # 找到 OK 標記之前、最近的 NG 標記
        preceding_ngs = [ng for ng in ng_markers if ng.end < ok.start]

        if preceding_ngs:
            # 從最近的 NG 結束處開始
            nearest_ng = preceding_ngs[-1]
            seg_start = max(0.0, nearest_ng.end + post_buffer)
        else:
            # 沒有前面的 NG，則從開頭或上一個 OK 結束處開始
            if segments:
                # 從上一個保留片段結束後開始
                seg_start = segments[-1].end
            else:
                seg_start = 0.0

        # 到 OK 標記開始處結束（OK 標記本身不保留）
        seg_end = min(total_duration, ok.start - pre_buffer)

        # 套用緩衝
        seg_start = max(0.0, seg_start - pre_buffer)
        seg_end = min(total_duration, seg_end + post_buffer)

        if seg_end > seg_start + 0.1:  # 至少 0.1 秒
            segments.append(
                Segment(
                    start=round(seg_start, 3),
                    end=round(seg_end, 3),
                    type="keep",
                    trigger_marker=ok,
                )
            )

    # 合併重疊片段
    segments = _merge_overlapping(segments)

    logger.info("回溯法切片完成，保留 %d 個片段", len(segments))
    return segments


def slice_interval(
    markers: list[Marker],
    transcript: list[TranscriptSegment],
    total_duration: float,
    pre_buffer: float = 0.5,
    post_buffer: float = 0.3,
) -> list[Segment]:
    """
    區間法切片：保留 START ~ END 之間的內容。

    Args:
        markers: 偵測到的標記列表
        transcript: 逐字稿
        total_duration: 影片總時長
        pre_buffer: 切點前緩衝（秒）
        post_buffer: 切點後緩衝（秒）

    Returns:
        切片結果列表
    """
    segments: list[Segment] = []

    start_markers = [m for m in markers if m.type == MarkerType.START]
    end_markers = [m for m in markers if m.type == MarkerType.END]

    if not start_markers:
        logger.warning("未偵測到 START 標記，無法進行區間法切片")
        return segments

    # 配對 START 和 END
    for start_m in start_markers:
        # 找到 START 之後最近的 END
        matching_ends = [e for e in end_markers if e.start > start_m.end]

        if matching_ends:
            end_m = matching_ends[0]
            seg_start = max(0.0, start_m.end + post_buffer - pre_buffer)
            seg_end = min(total_duration, end_m.start - post_buffer + post_buffer)
        else:
            # 沒有對應 END，取到下一個 START 或影片結束
            next_starts = [s for s in start_markers if s.start > start_m.end]
            if next_starts:
                seg_end = next_starts[0].start
            else:
                seg_end = total_duration
            seg_start = max(0.0, start_m.end + post_buffer - pre_buffer)
            end_m = None

        if seg_end > seg_start + 0.1:
            segments.append(
                Segment(
                    start=round(seg_start, 3),
                    end=round(seg_end, 3),
                    type="keep",
                    trigger_marker=start_m,
                )
            )

    segments = _merge_overlapping(segments)

    logger.info("區間法切片完成，保留 %d 個片段", len(segments))
    return segments


def _merge_overlapping(segments: list[Segment]) -> list[Segment]:
    """合併重疊或相鄰的片段"""
    if not segments:
        return segments

    # 依開始時間排序
    sorted_segs = sorted(segments, key=lambda s: s.start)
    merged: list[Segment] = [sorted_segs[0]]

    for seg in sorted_segs[1:]:
        last = merged[-1]
        if seg.start <= last.end + 0.05:  # 容差 50ms
            # 合併：延伸結束時間
            last.end = max(last.end, seg.end)
        else:
            merged.append(seg)

    return merged
