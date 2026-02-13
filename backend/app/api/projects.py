"""
ClipFlow AI — 專案管理 API 路由
處理專案 CRUD、影片上傳、AI 分析觸發
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks

from app.models.schemas import (
    Project,
    ProjectCreate,
    ProjectSettings,
    ProjectStatus,
    AnalysisStatus,
    SliceMode,
)
from app.models.store import (
    save_project,
    load_project,
    list_projects,
    delete_project,
    get_video_path,
    get_audio_path,
    save_transcript,
    load_transcript,
    save_segments,
    load_segments,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["專案管理"])


@router.post("", response_model=Project)
async def create_project(body: ProjectCreate):
    """建立新專案"""
    project = Project(
        name=body.name,
        settings=body.settings or ProjectSettings(),
    )
    save_project(project)
    logger.info("建立專案：%s (%s)", project.name, project.id)
    return project


@router.get("", response_model=list[Project])
async def get_projects():
    """列出所有專案"""
    return list_projects()


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """取得專案詳情"""
    project = load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project


@router.delete("/{project_id}")
async def remove_project(project_id: str):
    """刪除專案"""
    if not delete_project(project_id):
        raise HTTPException(status_code=404, detail="專案不存在")
    return {"message": "專案已刪除"}


@router.post("/{project_id}/upload")
async def upload_video(project_id: str, file: UploadFile = File(...)):
    """上傳影片檔案"""
    project = load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    # 驗證檔案類型
    allowed = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".mts"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的檔案格式：{suffix}。支援格式：{', '.join(allowed)}"
        )

    # 儲存檔案
    from app.models.store import _project_dir, _ensure_dir
    media_dir = _project_dir(project_id) / "media"
    _ensure_dir(media_dir)

    dest = media_dir / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 更新專案狀態
    project.status = ProjectStatus.UPLOADED
    project.source_file = str(dest)
    project.source_filename = file.filename
    save_project(project)

    logger.info("影片已上傳：%s -> %s", file.filename, dest)
    return {"message": "上傳成功", "filename": file.filename}


def _run_analysis(project_id: str):
    """背景執行 AI 分析流程（同步函式，由 BackgroundTasks 呼叫）"""
    from app.core.audio import extract_audio, get_video_duration
    from app.core.transcribe import transcribe
    from app.core.marker import detect_markers
    from app.core.slicer import slice_backtrack, slice_interval

    project = load_project(project_id)
    if not project:
        return

    try:
        project.status = ProjectStatus.ANALYZING
        project.progress = 0.0
        save_project(project)

        video_path = get_video_path(project_id)
        if not video_path:
            raise FileNotFoundError("找不到影片檔案")

        # 步驟 1：取得影片時長
        project.progress = 0.05
        save_project(project)
        duration = get_video_duration(video_path)
        project.duration_seconds = duration

        # 步驟 2：音訊提取
        project.progress = 0.1
        save_project(project)
        audio_path = get_audio_path(project_id)
        extract_audio(video_path, audio_path)

        # 步驟 3：語音轉文字
        project.progress = 0.2
        save_project(project)

        def on_stt_progress(p: float):
            project.progress = 0.2 + p * 0.5  # 20% ~ 70%
            save_project(project)

        transcript_segments = transcribe(
            audio_path,
            language=project.settings.language,
            model_size=project.settings.model_size,
            on_progress=on_stt_progress,
        )
        save_transcript(project_id, transcript_segments)

        # 步驟 4：標記詞偵測
        project.progress = 0.75
        save_project(project)
        markers = detect_markers(
            transcript_segments,
            ng_keywords=project.settings.ng_keywords,
            ok_keywords=project.settings.ok_keywords,
            start_keywords=project.settings.start_keywords,
            end_keywords=project.settings.end_keywords,
        )

        # 步驟 5：片段切片
        project.progress = 0.85
        save_project(project)

        if project.settings.mode == SliceMode.INTERVAL:
            segments = slice_interval(
                markers, transcript_segments, duration,
                project.settings.pre_buffer,
                project.settings.post_buffer,
            )
        else:
            segments = slice_backtrack(
                markers, transcript_segments, duration,
                project.settings.pre_buffer,
                project.settings.post_buffer,
            )

        save_segments(project_id, segments)

        # 完成
        project.status = ProjectStatus.ANALYZED
        project.progress = 1.0
        save_project(project)
        logger.info("專案 %s 分析完成，保留 %d 個片段", project_id, len(segments))

    except Exception as e:
        logger.exception("分析失敗：%s", e)
        project.status = ProjectStatus.ERROR
        project.error_message = str(e)
        save_project(project)


@router.post("/{project_id}/analyze")
async def analyze_project(project_id: str, background_tasks: BackgroundTasks):
    """觸發 AI 分析（背景執行）"""
    project = load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    if project.status == ProjectStatus.ANALYZING:
        raise HTTPException(status_code=409, detail="專案正在分析中")

    video_path = get_video_path(project_id)
    if not video_path:
        raise HTTPException(status_code=400, detail="請先上傳影片")

    background_tasks.add_task(_run_analysis, project_id)
    return {"message": "開始分析", "project_id": project_id}


@router.get("/{project_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(project_id: str):
    """查詢分析進度"""
    project = load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return AnalysisStatus(
        status=project.status,
        progress=project.progress,
        error_message=project.error_message,
    )


@router.get("/{project_id}/transcript")
async def get_transcript(project_id: str):
    """取得逐字稿"""
    transcript = load_transcript(project_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="尚未產生逐字稿")
    return transcript
