"""
ClipFlow AI — 匯出 API 路由
EDL / XML / SRT / 合併影片 匯出
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse


def _safe_disposition(filename: str) -> str:
    """產生同時支援 ASCII 回退和 UTF-8 的 Content-Disposition 值"""
    encoded = quote(filename)
    return f"attachment; filename=\"export\"; filename*=UTF-8''{encoded}"

from app.core.audio import concat_segments_to_video
from app.core.exporter import export_edl, export_xml, export_srt
from app.models.store import (
    load_project,
    load_segments,
    load_transcript,
    get_video_path,
    get_export_dir,
)

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["匯出"])


def _get_enabled_segments(project_id: str):
    """取得已啟用的保留片段"""
    project = load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    segments = load_segments(project_id)
    if not segments:
        raise HTTPException(status_code=400, detail="尚無切片資料")

    return project, segments


@router.post("/edl")
async def export_edl_file(project_id: str):
    """匯出 EDL 檔案"""
    project, segments = _get_enabled_segments(project_id)

    content = export_edl(
        segments,
        source_filename=project.source_filename or "source.mp4",
        title=f"{project.name}_clipflow",
    )

    # 同時存檔
    export_dir = get_export_dir(project_id)
    (export_dir / f"{project.name}.edl").write_text(content, encoding="utf-8")

    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": _safe_disposition(f"{project.name}.edl")},
    )


@router.post("/xml")
async def export_xml_file(project_id: str):
    """匯出 FCP XML 檔案"""
    project, segments = _get_enabled_segments(project_id)

    content = export_xml(
        segments,
        source_filename=project.source_filename or "source.mp4",
        title=f"{project.name}_clipflow",
    )

    export_dir = get_export_dir(project_id)
    (export_dir / f"{project.name}.xml").write_text(content, encoding="utf-8")

    return PlainTextResponse(
        content=content,
        media_type="application/xml",
        headers={"Content-Disposition": _safe_disposition(f"{project.name}.xml")},
    )


@router.post("/srt")
async def export_srt_file(project_id: str):
    """匯出 SRT 字幕檔"""
    project, segments = _get_enabled_segments(project_id)

    transcript = load_transcript(project_id)
    if not transcript:
        raise HTTPException(status_code=400, detail="尚無逐字稿資料")

    # 合併所有標記詞作為過濾清單
    filter_kw = (
        project.settings.ng_keywords
        + project.settings.ok_keywords
        + project.settings.start_keywords
        + project.settings.end_keywords
    )

    content = export_srt(segments, transcript, filter_keywords=filter_kw)

    export_dir = get_export_dir(project_id)
    (export_dir / f"{project.name}.srt").write_text(content, encoding="utf-8")

    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": _safe_disposition(f"{project.name}.srt")},
    )


@router.post("/video")
async def export_video_file(project_id: str):
    """匯出合併 MP4 影片"""
    project, segments = _get_enabled_segments(project_id)

    video_path = get_video_path(project_id)
    if not video_path:
        raise HTTPException(status_code=400, detail="找不到原始影片")

    enabled = [
        (s.start, s.end)
        for s in segments
        if s.enabled and s.type == "keep"
    ]
    if not enabled:
        raise HTTPException(status_code=400, detail="沒有啟用的保留片段")

    export_dir = get_export_dir(project_id)
    output = export_dir / f"{project.name}_export.mp4"

    concat_segments_to_video(video_path, enabled, output)

    return FileResponse(
        path=str(output),
        media_type="video/mp4",
        headers={"Content-Disposition": _safe_disposition(f"{project.name}_export.mp4")},
    )
