"""
ClipFlow AI — Pydantic 資料模型
定義專案、逐字稿、標記、片段等核心結構
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── 列舉型別 ────────────────────────────────────────────

class MarkerType(str, Enum):
    """標記類型"""
    NG = "NG"
    OK = "OK"
    START = "START"
    END = "END"


class SliceMode(str, Enum):
    """切片模式"""
    BACKTRACK = "backtrack"  # 回溯法
    INTERVAL = "interval"   # 區間法


class ProjectStatus(str, Enum):
    """專案處理狀態"""
    CREATED = "created"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    ERROR = "error"


# ─── 設定模型 ────────────────────────────────────────────

class ProjectSettings(BaseModel):
    """單一專案的分析設定"""
    mode: SliceMode = SliceMode.BACKTRACK
    language: str = "zh"
    model_size: str = "base"
    ng_keywords: list[str] = Field(default_factory=lambda: ["再來", "NG", "重來"])
    ok_keywords: list[str] = Field(default_factory=lambda: ["這段OK", "OK", "收"])
    start_keywords: list[str] = Field(default_factory=lambda: ["開始"])
    end_keywords: list[str] = Field(default_factory=lambda: ["結束"])
    pre_buffer: float = 0.5
    post_buffer: float = 0.3
    silence_threshold_db: float = -40.0
    silence_min_duration: float = 1.5


class UserSettings(BaseModel):
    """使用者全域偏好設定"""
    default_settings: ProjectSettings = Field(default_factory=ProjectSettings)
    default_language: str = "zh"
    default_model_size: str = "base"


# ─── 逐字稿模型 ──────────────────────────────────────────

class TranscriptWord(BaseModel):
    """帶時間戳的逐字稿詞語"""
    word: str
    start: float
    end: float
    confidence: float = 0.0


class TranscriptSegment(BaseModel):
    """Whisper 回傳的語句段落"""
    text: str
    start: float
    end: float
    words: list[TranscriptWord] = Field(default_factory=list)


# ─── 標記模型 ────────────────────────────────────────────

class Marker(BaseModel):
    """偵測到的語音標記"""
    type: MarkerType
    word: str
    start: float
    end: float
    confidence: float = 0.0


# ─── 片段模型 ────────────────────────────────────────────

class Segment(BaseModel):
    """切片後的片段"""
    id: str = Field(default_factory=lambda: f"seg_{uuid.uuid4().hex[:8]}")
    type: str = "keep"  # "keep" 或 "discard"
    start: float
    end: float
    trigger_marker: Optional[Marker] = None
    enabled: bool = True
    manual_adjusted: bool = False


# ─── 專案模型 ────────────────────────────────────────────

class Project(BaseModel):
    """專案主結構"""
    id: str = Field(default_factory=lambda: f"proj_{uuid.uuid4().hex[:8]}")
    name: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: ProjectStatus = ProjectStatus.CREATED
    source_file: Optional[str] = None
    source_filename: Optional[str] = None
    duration_seconds: Optional[float] = None
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    error_message: Optional[str] = None
    progress: float = 0.0  # 0.0 ~ 1.0


# ─── API 請求/回應模型 ────────────────────────────────────

class ProjectCreate(BaseModel):
    """建立專案請求"""
    name: str
    settings: Optional[ProjectSettings] = None


class SegmentUpdate(BaseModel):
    """更新片段切點"""
    start: Optional[float] = None
    end: Optional[float] = None


class AnalysisStatus(BaseModel):
    """分析進度回應"""
    status: ProjectStatus
    progress: float
    error_message: Optional[str] = None
