"""
ClipFlow AI — 片段操作 API 路由
片段查詢、切點調整、啟停用
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import Segment, SegmentUpdate
from app.models.store import load_project, load_segments, save_segments

router = APIRouter(prefix="/api/projects/{project_id}/segments", tags=["片段操作"])


@router.get("", response_model=list[Segment])
async def get_segments(project_id: str):
    """取得所有切片結果"""
    project = load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    segments = load_segments(project_id)
    if segments is None:
        return []
    return segments


@router.patch("/{segment_id}", response_model=Segment)
async def update_segment(project_id: str, segment_id: str, body: SegmentUpdate):
    """手動調整片段切點"""
    segments = load_segments(project_id)
    if segments is None:
        raise HTTPException(status_code=404, detail="尚無切片資料")

    target = None
    for seg in segments:
        if seg.id == segment_id:
            target = seg
            break

    if not target:
        raise HTTPException(status_code=404, detail="片段不存在")

    if body.start is not None:
        target.start = body.start
    if body.end is not None:
        target.end = body.end
    target.manual_adjusted = True

    save_segments(project_id, segments)
    return target


@router.put("/{segment_id}/toggle", response_model=Segment)
async def toggle_segment(project_id: str, segment_id: str):
    """啟用/停用片段"""
    segments = load_segments(project_id)
    if segments is None:
        raise HTTPException(status_code=404, detail="尚無切片資料")

    target = None
    for seg in segments:
        if seg.id == segment_id:
            target = seg
            break

    if not target:
        raise HTTPException(status_code=404, detail="片段不存在")

    target.enabled = not target.enabled
    save_segments(project_id, segments)
    return target
