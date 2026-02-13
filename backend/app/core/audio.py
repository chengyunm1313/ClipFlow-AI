"""
ClipFlow AI — 音訊提取模組
使用 FFmpeg 從影片中分離/轉換音軌
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def extract_audio(video_path: str | Path, output_path: str | Path) -> Path:
    """
    從影片中提取音訊，轉換為 16kHz mono WAV（Whisper 要求格式）

    Args:
        video_path: 原始影片路徑
        output_path: 輸出 WAV 檔案路徑

    Returns:
        輸出檔案的 Path

    Raises:
        RuntimeError: FFmpeg 執行失敗
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"影片檔案不存在：{video_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                # 覆蓋既有檔案
        "-i", str(video_path),
        "-vn",               # 不處理影像
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",      # 16kHz 取樣率
        "-ac", "1",          # 單聲道
        str(output_path),
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 音訊提取失敗：{result.stderr[-500:]}")

    return output_path


def get_video_duration(video_path: str | Path) -> float:
    """
    使用 FFprobe 取得影片時長（秒）

    Args:
        video_path: 影片路徑

    Returns:
        影片總秒數
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe 執行失敗：{result.stderr[-300:]}")

    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def concat_segments_to_video(
    source_path: str | Path,
    segments: list[tuple[float, float]],
    output_path: str | Path,
) -> Path:
    """
    使用 FFmpeg 串接多個片段為單一影片

    Args:
        source_path: 原始影片路徑
        segments: [(start_sec, end_sec), ...] 要保留的片段
        output_path: 輸出影片路徑

    Returns:
        輸出檔案的 Path
    """
    source_path = Path(source_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not segments:
        raise ValueError("沒有片段可供匯出")

    # 建構 FFmpeg 複合濾鏡
    filter_parts = []
    concat_inputs = []
    for i, (start, end) in enumerate(segments):
        duration = end - start
        filter_parts.append(
            f"[0:v]trim=start={start:.3f}:duration={duration:.3f},"
            f"setpts=PTS-STARTPTS[v{i}];"
            f"[0:a]atrim=start={start:.3f}:duration={duration:.3f},"
            f"asetpts=PTS-STARTPTS[a{i}];"
        )
        concat_inputs.append(f"[v{i}][a{i}]")

    filter_complex = "".join(filter_parts)
    filter_complex += "".join(concat_inputs)
    filter_complex += f"concat=n={len(segments)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(source_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 影片合併失敗：{result.stderr[-500:]}")

    return output_path
