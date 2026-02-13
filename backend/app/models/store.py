"""
ClipFlow AI — 本地 JSON 檔案儲存層
專案資料以 JSON 檔案形式儲存於 data/ 目錄
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from app.models.schemas import (
    Project,
    Segment,
    TranscriptSegment,
    UserSettings,
)

# 資料根目錄
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


def _ensure_dir(path: Path) -> None:
    """確保目錄存在"""
    path.mkdir(parents=True, exist_ok=True)


def _project_dir(project_id: str) -> Path:
    """取得專案資料目錄路徑"""
    return DATA_DIR / project_id


# ─── 專案 CRUD ──────────────────────────────────────────

def save_project(project: Project) -> None:
    """儲存專案 metadata"""
    pdir = _project_dir(project.id)
    _ensure_dir(pdir)
    (pdir / "project.json").write_text(
        project.model_dump_json(indent=2), encoding="utf-8"
    )


def load_project(project_id: str) -> Optional[Project]:
    """載入專案 metadata"""
    f = _project_dir(project_id) / "project.json"
    if not f.exists():
        return None
    return Project.model_validate_json(f.read_text(encoding="utf-8"))


def list_projects() -> list[Project]:
    """列出所有專案"""
    _ensure_dir(DATA_DIR)
    projects = []
    for d in sorted(DATA_DIR.iterdir()):
        pf = d / "project.json"
        if d.is_dir() and pf.exists():
            try:
                projects.append(
                    Project.model_validate_json(pf.read_text(encoding="utf-8"))
                )
            except Exception:
                continue
    return projects


def delete_project(project_id: str) -> bool:
    """刪除專案及其所有資料"""
    pdir = _project_dir(project_id)
    if not pdir.exists():
        return False
    shutil.rmtree(pdir)
    return True


# ─── 逐字稿 ────────────────────────────────────────────

def save_transcript(project_id: str, segments: list[TranscriptSegment]) -> None:
    """儲存逐字稿"""
    pdir = _project_dir(project_id)
    _ensure_dir(pdir)
    data = [s.model_dump() for s in segments]
    (pdir / "transcript.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_transcript(project_id: str) -> Optional[list[TranscriptSegment]]:
    """載入逐字稿"""
    f = _project_dir(project_id) / "transcript.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    return [TranscriptSegment.model_validate(d) for d in data]


# ─── 片段 ──────────────────────────────────────────────

def save_segments(project_id: str, segments: list[Segment]) -> None:
    """儲存切片結果"""
    pdir = _project_dir(project_id)
    _ensure_dir(pdir)
    data = [s.model_dump() for s in segments]
    (pdir / "segments.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_segments(project_id: str) -> Optional[list[Segment]]:
    """載入切片結果"""
    f = _project_dir(project_id) / "segments.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    return [Segment.model_validate(d) for d in data]


# ─── 影片檔案路徑 ───────────────────────────────────────

def get_video_path(project_id: str) -> Optional[Path]:
    """取得專案影片路徑"""
    pdir = _project_dir(project_id)
    media_dir = pdir / "media"
    if not media_dir.exists():
        return None
    # 回傳 media/ 下第一個影片檔
    for f in media_dir.iterdir():
        if f.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".mts"}:
            return f
    return None


def get_audio_path(project_id: str) -> Path:
    """取得音訊檔路徑（由 FFmpeg 產生）"""
    return _project_dir(project_id) / "audio.wav"


def get_export_dir(project_id: str) -> Path:
    """取得匯出目錄"""
    d = _project_dir(project_id) / "exports"
    _ensure_dir(d)
    return d


# ─── 設定 ──────────────────────────────────────────────

SETTINGS_FILE = DATA_DIR / "settings.json"


def load_settings() -> UserSettings:
    """載入使用者偏好設定"""
    _ensure_dir(DATA_DIR)
    if not SETTINGS_FILE.exists():
        return UserSettings()
    return UserSettings.model_validate_json(
        SETTINGS_FILE.read_text(encoding="utf-8")
    )


def save_settings(settings: UserSettings) -> None:
    """儲存使用者偏好設定"""
    _ensure_dir(DATA_DIR)
    SETTINGS_FILE.write_text(
        settings.model_dump_json(indent=2), encoding="utf-8"
    )
