"""等待至预约窗口前的最佳提交时刻；支持预热、多波次捡漏与账号错峰。"""

from __future__ import annotations

import datetime
import logging
import random
import time
from collections.abc import Callable

from .config_loader import ScheduleConfig

logger = logging.getLogger(__name__)


def _parse_hms(time_str: str) -> tuple[int, int, int]:
    parts = time_str.strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"时间格式应为 HH:MM:SS，当前: {time_str}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def clock_time_today(time_str: str) -> datetime.datetime:
    h, m, s = _parse_hms(time_str)
    now = datetime.datetime.now()
    return now.replace(hour=h, minute=m, second=s, microsecond=0)


def _sleep_until(target: datetime.datetime) -> None:
    while True:
        now = datetime.datetime.now()
        if now >= target:
            return
        remaining = (target - now).total_seconds()
        if remaining > 30:
            time.sleep(min(10, remaining - 5))
        elif remaining > 1:
            time.sleep(0.5)
        else:
            time.sleep(0.05)


def wait_until_clock_time(time_str: str, label: str = "") -> None:
    """等待至今日某一时刻（用于 9:05 / 9:10 捡漏波次）。"""
    target = clock_time_today(time_str)
    now = datetime.datetime.now()
    if now >= target:
        logger.info("%s 已过 %s，立即执行", label or "波次", time_str)
        return
    delta = (target - now).total_seconds()
    logger.info(
        "%s等待 %.0f 秒，将于 %s 执行",
        f"{label} " if label else "",
        delta,
        time_str,
    )
    _sleep_until(target)


def wait_until_reserve_time(
    cfg: ScheduleConfig,
    on_prewarm: Callable[[], None] | None = None,
    *,
    account_jitter: float | None = None,
    jitter_seconds: float = 0,
) -> None:
    """
    在 target_time 前 advance_seconds 秒触发。
    若配置 prewarm_minutes，则提前拉取门店/session 预热。
    account_jitter: 本账号额外偏移（秒）；未指定时在 jitter_seconds 内随机。
    """
    now = datetime.datetime.now()
    h, m, s = _parse_hms(cfg.target_time)
    target = now.replace(hour=h, minute=m, second=s, microsecond=0)
    jitter = account_jitter
    if jitter is None and jitter_seconds > 0:
        jitter = random.uniform(0, jitter_seconds)
    extra = jitter or 0
    fire_at = target - datetime.timedelta(seconds=cfg.advance_seconds + extra)

    if now >= target and not cfg.run_immediately_if_missed:
        logger.warning(
            "已过今日申购时间 %s，跳过等待。手动测试请设 run_immediately_if_missed: true",
            cfg.target_time,
        )
        return

    if cfg.prewarm_minutes > 0 and on_prewarm is not None:
        prewarm_at = fire_at - datetime.timedelta(minutes=cfg.prewarm_minutes)
        if datetime.datetime.now() < prewarm_at:
            logger.info(
                "将于 %s 预热（提前 %d 分钟）",
                prewarm_at.strftime("%H:%M:%S"),
                cfg.prewarm_minutes,
            )
            _sleep_until(prewarm_at)
            on_prewarm()

    if datetime.datetime.now() >= fire_at:
        logger.info("已到触发时刻，立即执行")
        return

    delta = (fire_at - datetime.datetime.now()).total_seconds()
    if extra:
        logger.info(
            "等待 %.1f 秒，将于 %s 发起预约（错峰偏移 %.1fs）",
            delta,
            fire_at.strftime("%H:%M:%S"),
            extra,
        )
    else:
        logger.info("等待 %.1f 秒，将于 %s 发起预约", delta, fire_at.strftime("%H:%M:%S"))
    _sleep_until(fire_at)
