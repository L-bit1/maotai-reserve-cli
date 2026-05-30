import yaml
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...core.config import settings
from ...core.response import ok
from ...services.imaotai_service import health_items
from ..deps import get_current_user

router = APIRouter(prefix="/settings", tags=["设置"])


class SettingsUpdate(BaseModel):
    schedule_target_time: str | None = None
    schedule_advance_seconds: int | None = None
    shop_strategy_default: str | None = None
    claim_energy_default: bool | None = None
    retry_count: int | None = None
    retry_interval_seconds: float | None = None
    session_wait_seconds: int | None = None
    pushplus_token: str | None = None


def _load_yaml() -> dict:
    if not settings.config_yaml.exists():
        return {}
    with open(settings.config_yaml, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _settings_view(raw: dict) -> dict:
    sched = raw.get("schedule", {}) or {}
    retry = raw.get("retry", {}) or {}
    session = raw.get("session", {}) or {}
    return {
        "schedule_target_time": sched.get("target_time", "09:00:00"),
        "schedule_advance_seconds": sched.get("advance_seconds", 2),
        "shop_strategy_default": raw.get("shop_strategy", "max_inventory"),
        "claim_energy_default": raw.get("claim_energy", True),
        "retry_count": retry.get("count", 3),
        "retry_interval_seconds": retry.get("interval_seconds", 0.5),
        "session_wait_seconds": session.get("wait_seconds", 120),
        "pushplus_token": "***" if raw.get("pushplus_token") else "",
        "amap_key": "***" if raw.get("amap_key") else "",
    }


@router.get("")
def get_settings(_: str = Depends(get_current_user)):
    return ok(_settings_view(_load_yaml()))


@router.put("")
def put_settings(body: SettingsUpdate, _: str = Depends(get_current_user)):
    raw = _load_yaml()
    if body.schedule_target_time is not None or body.schedule_advance_seconds is not None:
        raw.setdefault("schedule", {})
        if body.schedule_target_time is not None:
            raw["schedule"]["target_time"] = body.schedule_target_time
        if body.schedule_advance_seconds is not None:
            raw["schedule"]["advance_seconds"] = body.schedule_advance_seconds
    if body.shop_strategy_default is not None:
        raw["shop_strategy"] = body.shop_strategy_default
    if body.claim_energy_default is not None:
        raw["claim_energy"] = body.claim_energy_default
    if body.retry_count is not None or body.retry_interval_seconds is not None:
        raw.setdefault("retry", {})
        if body.retry_count is not None:
            raw["retry"]["count"] = body.retry_count
        if body.retry_interval_seconds is not None:
            raw["retry"]["interval_seconds"] = body.retry_interval_seconds
    if body.session_wait_seconds is not None:
        raw.setdefault("session", {})["wait_seconds"] = body.session_wait_seconds
    if body.pushplus_token is not None:
        raw["pushplus_token"] = body.pushplus_token
    with open(settings.config_yaml, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False)
    return ok(_settings_view(raw))


@router.get("/health")
def settings_health(_: str = Depends(get_current_user)):
    return ok({"items": health_items()})


@router.get("/scheduler")
def get_scheduler(_: str = Depends(get_current_user)):
    from ...services.scheduler_service import scheduler_status

    return ok(scheduler_status())
