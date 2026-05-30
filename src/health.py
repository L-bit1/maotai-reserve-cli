"""健康检查，返回结构化结果供 CLI 展示。"""

from __future__ import annotations

import datetime
import time
from dataclasses import dataclass, field

import requests

from .api import IMaotaiClient, fetch_app_version
from .config_loader import (
    CONFIG_PATH,
    CREDENTIALS_PATH,
    load_config,
    load_credentials,
    mask_mobile,
    validate_secret_key,
)
from .exceptions import ConfigError


@dataclass
class CheckItem:
    level: str  # ok | warn | fail
    category: str
    message: str


@dataclass
class HealthReport:
    items: list[CheckItem] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.items if i.level == "fail")

    @property
    def passed(self) -> bool:
        return self.error_count == 0


def run_health_check() -> HealthReport:
    report = HealthReport()

    def add(level: str, cat: str, msg: str) -> None:
        report.items.append(CheckItem(level, cat, msg))

    if not CONFIG_PATH.exists():
        add("fail", "配置", f"缺少 {CONFIG_PATH.name}")
        return report
    add("ok", "配置", "config.yaml 存在")

    cfg = None
    try:
        cfg = load_config()
        validate_secret_key(cfg.secret_key)
        add("ok", "配置", "secret_key 已设置")
    except (FileNotFoundError, ConfigError) as e:
        add("fail", "配置", str(e))
        return report

    if cfg.amap_key:
        add("ok", "配置", "amap_key 已设置")
    else:
        add("warn", "配置", "amap_key 未填")
    add("ok", "配置", f"预约商品 {len(cfg.items)} 个")

    ad = cfg.antidetect
    if ad.enabled:
        mode = "稳定指纹" if ad.stable_fingerprint else "会话随机"
        add(
            "ok",
            "风控",
            f"已开启 | {mode} | 发码间隔≥{ad.login_vcode_interval:.0f}s | "
            f"预约≤{ad.max_reserve_per_minute}/分钟",
        )
        if len(cfg.proxy_pools) == 0:
            add("warn", "风控", "未配置 proxy_pools，多账号同 IP 易被关联")
    else:
        add("warn", "风控", "antidetect.enabled=false，多账号风险较高")

    try:
        ver = fetch_app_version()
        add("ok", "网络", f"App 版本 {ver}")
    except Exception as e:
        add("fail", "网络", f"版本接口: {e}")

    try:
        day_ms = int(time.mktime(datetime.date.today().timetuple()) * 1000)
        r = requests.get(
            f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/"
            f"index/session/get/{day_ms}",
            timeout=15,
        )
        sid = r.json().get("data", {}).get("sessionId")
        if sid and str(sid) != "0":
            add("ok", "网络", f"sessionId={sid}")
        else:
            add("warn", "网络", f"sessionId={sid}（可能非 9:00–10:00）")
    except Exception as e:
        add("fail", "网络", f"场次接口: {e}")

    if not CREDENTIALS_PATH.exists():
        add("warn", "账号", "未登录，请先添加账号")
        return report

    try:
        accounts = load_credentials(cfg.secret_key)
        add("ok", "账号", f"已加载 {len(accounts)} 个账号")
        app_ver = fetch_app_version()
        for acc in accounts:
            client = IMaotaiClient(
                acc,
                app_version=app_ver,
                proxy_pools=cfg.proxy_pools,
                antidetect=cfg.antidetect,
            )
            valid, msg = client.validate_token()
            label = mask_mobile(acc.mobile)
            add("ok" if valid else "fail", "账号", f"{label}: {msg}")
    except ConfigError as e:
        add("fail", "账号", str(e))

    return report
