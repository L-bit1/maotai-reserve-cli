"""风控：设备指纹、请求节流、限流冷却（多账号 / 同 IP 场景）。"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass

from .config_loader import AccountCredentials, AntidetectConfig
from .device_util import (
    DEFAULT_MT_INFO,
    generate_mt_info,
    profile_from_device_id,
    random_network_type,
    random_ua,
)

logger = logging.getLogger(__name__)

_FALLBACK_UA = "iOS;17.0;Apple;iPhone15,2"


@dataclass(frozen=True)
class DeviceProfile:
    """单账号会话内保持稳定的设备画像（模拟真机）。"""

    ua: str
    mt_info: str
    network_type: str


def resolve_device_profile(
    account: AccountCredentials,
    ad: AntidetectConfig,
) -> DeviceProfile:
    if not ad.enabled:
        return DeviceProfile(_FALLBACK_UA, DEFAULT_MT_INFO, "WIFI")

    if account.device_ua and account.device_mt_info:
        return DeviceProfile(
            account.device_ua,
            account.device_mt_info,
            account.device_network or "WIFI",
        )

    if ad.stable_fingerprint and account.device_id:
        ua, mt_info, net = profile_from_device_id(account.device_id)
        return DeviceProfile(ua, mt_info, net)

    mt_info = (
        generate_mt_info()
        if ad.random_mt_info
        else DEFAULT_MT_INFO
    )
    network = random_network_type() if ad.random_network_type else "WIFI"
    ua = random_ua() if ad.random_ua else _FALLBACK_UA
    return DeviceProfile(ua, mt_info, network)


def ensure_device_profile(
    account: AccountCredentials,
    ad: AntidetectConfig,
) -> AccountCredentials:
    """登录保存时写入稳定指纹，避免每次启动 UA/MT-Info 变化。"""
    if not ad.enabled or not ad.stable_fingerprint:
        return account
    if account.device_ua and account.device_mt_info:
        return account
    prof = resolve_device_profile(account, ad)
    account.device_ua = prof.ua
    account.device_mt_info = prof.mt_info
    account.device_network = prof.network_type
    return account


def throttle_key(mobile: str, egress_group: str = "") -> str:
    return f"{(egress_group or 'direct').strip()}:{mobile}"


class RequestThrottle:
    """进程内全账号共享的节流与冷却状态。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cooldown_until: dict[str, float] = {}
        self._last_vcode_at: dict[str, float] = {}
        self._reserve_at: dict[str, list[float]] = {}

    def cooldown_remaining(self, key: str) -> float:
        with self._lock:
            until = self._cooldown_until.get(key, 0)
            return max(0.0, until - time.time())

    def set_cooldown(self, key: str, seconds: float, reason: str = "") -> None:
        if seconds <= 0:
            return
        with self._lock:
            self._cooldown_until[key] = time.time() + seconds
        if reason:
            logger.warning("风控冷却 %s %.0fs: %s", key.split(":")[-1][-4:], seconds, reason)

    def assert_not_cooled(self, key: str) -> None:
        rem = self.cooldown_remaining(key)
        if rem > 0:
            from .exceptions import RateLimitError

            raise RateLimitError(
                f"账号处于限流冷却，请等待 {rem:.0f} 秒后再试。"
            )

    def pace(self, key: str, min_s: float, max_s: float) -> None:
        self.assert_not_cooled(key)
        if min_s <= 0 and max_s <= 0:
            return
        delay = random.uniform(max(0.05, min_s), max(min_s, max_s))
        time.sleep(delay)

    def can_send_vcode(self, mobile: str, interval: float) -> tuple[bool, str]:
        if interval <= 0:
            return True, ""
        with self._lock:
            last = self._last_vcode_at.get(mobile, 0)
            wait = interval - (time.time() - last)
        if wait > 0:
            return False, f"发码间隔过短，请 {wait:.0f} 秒后再试"
        return True, ""

    def record_vcode(self, mobile: str) -> None:
        with self._lock:
            self._last_vcode_at[mobile] = time.time()

    def can_reserve(self, key: str, max_per_minute: int) -> tuple[bool, str]:
        if max_per_minute <= 0:
            return True, ""
        now = time.time()
        with self._lock:
            times = [t for t in self._reserve_at.get(key, []) if now - t < 60]
            self._reserve_at[key] = times
            if len(times) >= max_per_minute:
                return False, f"本分钟预约请求已达 {max_per_minute} 次上限"
        return True, ""

    def record_reserve(self, key: str) -> None:
        with self._lock:
            self._reserve_at.setdefault(key, []).append(time.time())


_GLOBAL_THROTTLE = RequestThrottle()


def get_throttle() -> RequestThrottle:
    return _GLOBAL_THROTTLE


def is_rate_limited_status(status: int, body: str = "") -> bool:
    if status == 429:
        return True
    lower = (body or "").lower()
    return status in (403, 503) and any(
        x in lower for x in ("频繁", "限流", "too many", "rate", "风控")
    )
