"""
ClipFlow AI — 語音轉文字模組
使用 faster-whisper 進行本地語音辨識
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.models.schemas import TranscriptSegment, TranscriptWord

logger = logging.getLogger(__name__)

# 模型快取（避免重複載入）
_model_cache: dict[str, object] = {}


def _get_model(model_size: str = "base"):
    """
    取得或建立 faster-whisper 模型實例（帶快取）

    Args:
        model_size: 模型大小 (tiny/base/small/medium/large-v3)
    """
    if model_size not in _model_cache:
        from faster_whisper import WhisperModel

        logger.info("正在載入 Whisper 模型：%s（首次載入需下載）", model_size)
        # CPU 推論使用 int8 量化加速
        _model_cache[model_size] = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )
        logger.info("Whisper 模型 %s 載入完成", model_size)

    return _model_cache[model_size]


def transcribe(
    audio_path: str | Path,
    language: str = "zh",
    model_size: str = "base",
    on_progress: Optional[callable] = None,
) -> list[TranscriptSegment]:
    """
    對音訊檔案進行語音辨識

    Args:
        audio_path: WAV 音訊檔案路徑
        language: 語言代碼 (zh/en/ja/...)
        model_size: Whisper 模型大小
        on_progress: 進度回呼函式 (0.0~1.0)

    Returns:
        TranscriptSegment 列表（含逐字時間戳）
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"音訊檔案不存在：{audio_path}")

    model = _get_model(model_size)

    # 執行轉寫，啟用逐字時間戳
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,  # 啟用語音活動偵測過濾
    )

    logger.info(
        "音訊時長：%.1f 秒，偵測語言：%s (%.1f%%)",
        info.duration,
        info.language,
        info.language_probability * 100,
    )

    result: list[TranscriptSegment] = []
    total_duration = info.duration if info.duration > 0 else 1.0

    for segment in segments_iter:
        words = []
        if segment.words:
            for w in segment.words:
                words.append(
                    TranscriptWord(
                        word=w.word.strip(),
                        start=round(w.start, 3),
                        end=round(w.end, 3),
                        confidence=round(w.probability, 3) if w.probability else 0.0,
                    )
                )

        result.append(
            TranscriptSegment(
                text=segment.text.strip(),
                start=round(segment.start, 3),
                end=round(segment.end, 3),
                words=words,
            )
        )

        # 回報進度
        if on_progress and total_duration > 0:
            progress = min(segment.end / total_duration, 1.0)
            on_progress(progress)

    logger.info("轉寫完成，共 %d 個語句段落", len(result))
    return result
