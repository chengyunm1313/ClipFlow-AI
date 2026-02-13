"""
ClipFlow AI — 使用者偏好設定 API 路由
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import UserSettings
from app.models.store import load_settings, save_settings

router = APIRouter(prefix="/api/settings", tags=["設定"])


@router.get("", response_model=UserSettings)
async def get_settings():
    """取得使用者偏好設定"""
    return load_settings()


@router.put("", response_model=UserSettings)
async def update_settings(body: UserSettings):
    """更新使用者偏好設定"""
    save_settings(body)
    return body
