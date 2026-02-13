"""
ClipFlow AI — 匯出模組
產出 EDL / FCP XML / SRT 字幕 / 合併 MP4
"""

from __future__ import annotations

import math
from pathlib import Path

from app.models.schemas import Segment, TranscriptSegment


def _seconds_to_tc(seconds: float, fps: float = 30.0) -> str:
    """
    將秒數轉換為 SMPTE 時間碼 (HH:MM:SS:FF)

    Args:
        seconds: 秒數
        fps: 幀率

    Returns:
        時間碼字串
    """
    total_frames = int(round(seconds * fps))
    ff = total_frames % int(fps)
    total_seconds = total_frames // int(fps)
    ss = total_seconds % 60
    mm = (total_seconds // 60) % 60
    hh = total_seconds // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _seconds_to_srt_tc(seconds: float) -> str:
    """
    將秒數轉換為 SRT 時間碼 (HH:MM:SS,mmm)
    """
    ms = int(round((seconds % 1) * 1000))
    total_s = int(seconds)
    ss = total_s % 60
    mm = (total_s // 60) % 60
    hh = total_s // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


# ─── EDL 匯出 ───────────────────────────────────────────

def export_edl(
    segments: list[Segment],
    source_filename: str,
    fps: float = 30.0,
    title: str = "ClipFlow Export",
) -> str:
    """
    生成 CMX 3600 EDL 格式字串

    Args:
        segments: 保留的片段列表
        source_filename: 原始檔案名稱
        fps: 幀率
        title: EDL 標題

    Returns:
        EDL 內容字串
    """
    enabled = [s for s in segments if s.enabled and s.type == "keep"]
    enabled.sort(key=lambda s: s.start)

    lines = [
        f"TITLE: {title}",
        "FCM: NON-DROP FRAME",
        "",
    ]

    # 計算累積的 record 時間軸位置
    record_offset = 0.0

    for i, seg in enumerate(enabled, 1):
        duration = seg.end - seg.start
        src_in = _seconds_to_tc(seg.start, fps)
        src_out = _seconds_to_tc(seg.end, fps)
        rec_in = _seconds_to_tc(record_offset, fps)
        rec_out = _seconds_to_tc(record_offset + duration, fps)

        lines.append(
            f"{i:03d}  AX       AA/V  C        "
            f"{src_in} {src_out} {rec_in} {rec_out}"
        )
        lines.append(f"* FROM CLIP NAME: {source_filename}")
        lines.append("")

        record_offset += duration

    return "\n".join(lines)


# ─── FCP XML 匯出 ────────────────────────────────────────

def export_xml(
    segments: list[Segment],
    source_filename: str,
    fps: float = 30.0,
    title: str = "ClipFlow Export",
) -> str:
    """
    生成 Final Cut Pro XML (XMEML) 格式字串

    Args:
        segments: 保留的片段列表
        source_filename: 原始檔案名稱
        fps: 幀率
        title: 序列名稱

    Returns:
        XML 內容字串
    """
    enabled = [s for s in segments if s.enabled and s.type == "keep"]
    enabled.sort(key=lambda s: s.start)

    fps_int = int(round(fps))
    total_frames = sum(
        int(round((s.end - s.start) * fps)) for s in enabled
    )

    # XML 片段
    clip_items = []
    timeline_offset = 0

    for i, seg in enumerate(enabled, 1):
        seg_frames = int(round((seg.end - seg.start) * fps))
        in_frame = int(round(seg.start * fps))
        out_frame = int(round(seg.end * fps))

        clip_items.append(f"""
            <clipitem id="clipitem-{i}">
                <name>{source_filename}</name>
                <duration>{seg_frames}</duration>
                <rate><timebase>{fps_int}</timebase><ntsc>FALSE</ntsc></rate>
                <start>{timeline_offset}</start>
                <end>{timeline_offset + seg_frames}</end>
                <in>{in_frame}</in>
                <out>{out_frame}</out>
                <file id="file-1">
                    <name>{source_filename}</name>
                    <rate><timebase>{fps_int}</timebase><ntsc>FALSE</ntsc></rate>
                </file>
            </clipitem>""")

        timeline_offset += seg_frames

    clips_xml = "\n".join(clip_items)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
    <sequence>
        <name>{title}</name>
        <duration>{total_frames}</duration>
        <rate><timebase>{fps_int}</timebase><ntsc>FALSE</ntsc></rate>
        <media>
            <video>
                <track>{clips_xml}
                </track>
            </video>
        </media>
    </sequence>
</xmeml>"""

    return xml


# ─── SRT 字幕匯出 ────────────────────────────────────────

def export_srt(
    segments: list[Segment],
    transcript: list[TranscriptSegment],
    filter_keywords: list[str] | None = None,
) -> str:
    """
    生成 SRT 字幕，僅包含保留片段中的文字，並過濾標記詞

    Args:
        segments: 保留的片段列表
        transcript: 完整逐字稿
        filter_keywords: 要過濾的標記詞列表

    Returns:
        SRT 內容字串
    """
    filter_keywords = [kw.lower() for kw in (filter_keywords or [])]
    enabled = [s for s in segments if s.enabled and s.type == "keep"]
    enabled.sort(key=lambda s: s.start)

    srt_entries = []
    counter = 1

    # 計算保留片段的累積時間偏移
    time_offset = 0.0

    for seg in enabled:
        seg_duration = seg.end - seg.start

        # 找出落在此片段內的逐字稿段落
        for ts in transcript:
            # 逐字稿段落與保留片段有交集
            if ts.end <= seg.start or ts.start >= seg.end:
                continue

            # 裁剪到片段範圍內
            sub_start = max(ts.start, seg.start)
            sub_end = min(ts.end, seg.end)

            # 過濾標記詞
            text = ts.text
            for kw in filter_keywords:
                text = text.lower().replace(kw, "").strip()
            # 還原大小寫（使用原始文字）
            if filter_keywords:
                clean_text = ts.text
                for kw in filter_keywords:
                    # 不區分大小寫移除
                    import re
                    clean_text = re.sub(
                        re.escape(kw), "", clean_text, flags=re.IGNORECASE
                    ).strip()
                text = clean_text

            if not text:
                continue

            # 轉換為相對於匯出影片的時間
            rel_start = time_offset + (sub_start - seg.start)
            rel_end = time_offset + (sub_end - seg.start)

            srt_entries.append(
                f"{counter}\n"
                f"{_seconds_to_srt_tc(rel_start)} --> {_seconds_to_srt_tc(rel_end)}\n"
                f"{text}\n"
            )
            counter += 1

        time_offset += seg_duration

    return "\n".join(srt_entries)
