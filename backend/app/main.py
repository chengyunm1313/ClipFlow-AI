"""
ClipFlow AI — FastAPI 主進入點
掛載所有路由、設定 CORS、啟動時系統檢查
"""

from __future__ import annotations

import logging
import shutil
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api import projects, segments, export, settings

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("clipflow")


def check_dependencies():
    """啟動時檢查系統依賴"""
    # 檢查 FFmpeg
    if not shutil.which("ffmpeg"):
        logger.error("❌ 找不到 FFmpeg，請先安裝：brew install ffmpeg")
        sys.exit(1)

    if not shutil.which("ffprobe"):
        logger.error("❌ 找不到 FFprobe，請先安裝：brew install ffmpeg")
        sys.exit(1)

    logger.info("✅ FFmpeg 已就緒")


# 建立 FastAPI 應用
app = FastAPI(
    title="ClipFlow AI",
    description="AI 語音標記自動粗剪工具 — 地端 API",
    version="0.1.0",
)

# CORS 設定：允許本地前端存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載 API 路由
app.include_router(projects.router)
app.include_router(segments.router)
app.include_router(export.router)
app.include_router(settings.router)

# 掛載靜態檔案（提供影片預覽用）
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")


@app.on_event("startup")
async def startup():
    """應用啟動事件"""
    check_dependencies()
    logger.info("🚀 ClipFlow AI 啟動完成 — http://localhost:8000")
    logger.info("📖 API 文件：http://localhost:8000/docs")


@app.get("/api/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "ok", "service": "ClipFlow AI"}
