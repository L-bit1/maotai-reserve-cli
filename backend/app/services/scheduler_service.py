"""服务器定时任务：每日预约、中签同步、Token 巡检、周末欢乐购。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..core.config import settings
from .imaotai_service import get_app_config

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _parse_hms(value: str) -> tuple[int, int, int]:
    parts = (value or "09:00:00").strip().split(":")
    h = int(parts[0]) if len(parts) > 0 else 9
    m = int(parts[1]) if len(parts) > 1 else 0
    s = int(parts[2]) if len(parts) > 2 else 0
    return h, m, s


def _reserve_start_time() -> tuple[int, int]:
    """计算应启动 execute_reserve 的时刻（含预热提前量）。"""
    cfg = get_app_config()
    h, m, s = _parse_hms(cfg.schedule.target_time)
    now = datetime.now()
    target = now.replace(hour=h, minute=m, second=s, microsecond=0)
    fire_at = target - timedelta(seconds=cfg.schedule.advance_seconds)
    prewarm_at = fire_at - timedelta(minutes=max(0, cfg.schedule.prewarm_minutes))
    start_at = prewarm_at - timedelta(minutes=1)
    return start_at.hour, start_at.minute


def _job_daily_reserve() -> None:
    from .reserve_service import is_scheduled_reserve_running, run_reserve_in_background

    if is_scheduled_reserve_running():
        logger.warning("已有预约任务在运行，跳过本次定时")
        return
    logger.info("定时任务：每日申购预约开始")
    run_reserve_in_background(
        dry_run=False,
        skip_wait=False,
        job_name="定时每日预约",
    )


def _job_lottery_sync() -> None:
    logger.info("定时任务：同步中签结果")
    from .lottery_sync_service import sync_all_accounts

    synced, pending, errors = sync_all_accounts()
    if errors:
        logger.warning("中签同步部分失败: %s", errors[:5])
    logger.info("中签同步完成 synced=%s pending=%s", synced, pending)


def _job_token_check() -> None:
    logger.info("定时任务：Token 巡检")
    from ..core.database import SessionLocal
    from ..models.entities import Account
    from .imaotai_service import validate_token, get_app_config
    from src.notify import push_pushplus

    db = SessionLocal()
    invalid: list[str] = []
    try:
        accounts = db.query(Account).filter(Account.enabled == True).all()  # noqa: E712
        for acc in accounts:
            if not acc.token_enc:
                invalid.append(f"{acc.mobile}(未登录)")
                continue
            ok, msg = validate_token(acc)
            if not ok:
                invalid.append(f"{acc.mobile}({msg})")
                acc.last_error = msg[:500]
        db.commit()
        cfg = get_app_config()
        if invalid and cfg.pushplus_token:
            push_pushplus(
                cfg.pushplus_token,
                f"i茅台 Token 异常 {len(invalid)} 个",
                "\n".join(invalid[:50]),
            )
    finally:
        db.close()


def _job_weekend_happy() -> None:
    logger.info("定时任务：周末欢乐购")
    from ..core.database import SessionLocal
    from ..models.entities import Account
    from .weekend_executor import _run_weekend

    db = SessionLocal()
    try:
        ids = [a.id for a in db.query(Account).filter(Account.enabled == True).all()]  # noqa: E712
    finally:
        db.close()
    if ids:
        _run_weekend(ids)


def start_scheduler() -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("定时任务未启用 (MT_SCHEDULER_ENABLED=false)")
        return
    if _scheduler is not None:
        return

    tz = settings.scheduler_timezone
    _scheduler = BackgroundScheduler(timezone=tz)

    rh, rm = _reserve_start_time()
    _scheduler.add_job(
        _job_daily_reserve,
        CronTrigger(hour=rh, minute=rm, timezone=tz),
        id="daily_reserve",
        replace_existing=True,
    )

    lh, lm = _parse_hms(settings.lottery_check_time)[:2]
    _scheduler.add_job(
        _job_lottery_sync,
        CronTrigger(hour=lh, minute=lm, timezone=tz),
        id="lottery_sync",
        replace_existing=True,
    )

    th, tm = _parse_hms(settings.token_check_time)[:2]
    _scheduler.add_job(
        _job_token_check,
        CronTrigger(hour=th, minute=tm, timezone=tz),
        id="token_check",
        replace_existing=True,
    )

    if settings.weekend_reserve_enabled:
        wh, wm = _parse_hms(settings.weekend_reserve_time)[:2]
        _scheduler.add_job(
            _job_weekend_happy,
            CronTrigger(day_of_week="sun", hour=wh, minute=wm, timezone=tz),
            id="weekend_happy",
            replace_existing=True,
        )

    _scheduler.start()
    logger.info(
        "定时任务已启动 tz=%s 预约=%02d:%02d 中签=%s Token=%s",
        tz,
        rh,
        rm,
        settings.lottery_check_time,
        settings.token_check_time,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def scheduler_status() -> dict:
    if _scheduler is None:
        return {"enabled": settings.scheduler_enabled, "running": False, "jobs": []}
    jobs = []
    for j in _scheduler.get_jobs():
        jobs.append(
            {
                "id": j.id,
                "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
            }
        )
    return {"enabled": True, "running": True, "jobs": jobs}
