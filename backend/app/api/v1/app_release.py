"""Android 应用内更新检查（无需登录）。"""

from fastapi import APIRouter, Query

from ...core.config import settings
from ...core.response import ok

router = APIRouter(prefix="/app", tags=["应用更新"])


@router.get("/check-update")
def check_update(version_code: int = Query(..., ge=1, description="当前 App 的 versionCode")):
    """
    比较客户端 versionCode 与服务器配置的最新版本。
    发布新版本时：上传 APK 到 /downloads/，并增大 MT_APP_LATEST_VERSION_CODE。
    """
    latest = settings.app_latest_version_code
    has_update = version_code < latest
    download_url = (settings.app_download_url or "").strip()
    if has_update and not download_url:
        download_url = _default_download_url()

    return ok(
        {
            "has_update": has_update,
            "version_code": latest,
            "version_name": settings.app_latest_version_name,
            "download_url": download_url if has_update else "",
            "release_notes": settings.app_release_notes if has_update else "",
            "force_update": settings.app_force_update if has_update else False,
        }
    )


def _default_download_url() -> str:
    """未配置 URL 时，按常见部署路径推断。"""
    base = (settings.cors_origins or "").split(",")[0].strip()
    if base.startswith("http"):
        return f"{base.rstrip('/')}/downloads/maotai-reserve.apk"
    return "http://139.155.134.97/downloads/maotai-reserve.apk"
