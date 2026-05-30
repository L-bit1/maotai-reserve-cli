"""封装一期 src 模块，供 API 调用。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api import IMaotaiClient, fetch_app_version, new_device_id
from src.config_loader import (
    AccountCredentials,
    AppConfig,
    load_config,
    load_credentials,
    mask_mobile,
    save_credentials,
)
from src.exceptions import AuthError, ConfigError, RateLimitError, SessionNotReadyError, TokenExpiredError
from src.health import run_health_check
from src.risk_control import ensure_device_profile

from ..models.entities import Account


def decrypt_account_token(acc: Account, secret_key: str) -> str:
    from src.crypto import decrypt_local

    if not acc.token_enc:
        return ""
    if acc.token_enc.startswith("enc:"):
        return decrypt_local(acc.token_enc[4:], secret_key)
    return acc.token_enc


def _to_credentials(acc: Account, cfg: AppConfig) -> AccountCredentials:
    token = decrypt_account_token(acc, cfg.secret_key)
    cred = AccountCredentials(
        mobile=acc.mobile,
        token=token,
        user_id=acc.user_id or "0",
        province=acc.province,
        city=acc.city,
        lat=acc.lat or "28.23",
        lng=acc.lng or "112.94",
        device_id=acc.device_id or new_device_id(),
        end_date=acc.end_date,
        receiver_name=acc.receiver_name,
        receiver_mobile=acc.receiver_mobile or acc.mobile,
        district=acc.district,
        detail_address=acc.detail_address,
        shop_id=acc.shop_id,
        shop_strategy=acc.shop_strategy,
        proxy_url=acc.proxy_url,
        egress_group=acc.egress_group,
        device_ua=acc.device_ua,
        device_mt_info=acc.device_mt_info,
        device_network=acc.device_network,
    )
    return ensure_device_profile(cred, cfg.antidetect)


def _encrypt_token(token: str, secret_key: str) -> str:
    from src.crypto import encrypt_local

    return "enc:" + encrypt_local(token, secret_key)


def get_app_config() -> AppConfig:
    return load_config()


def mask_mobile_api(mobile: str) -> str:
    return mask_mobile(mobile)


def client_for_account(acc: Account) -> IMaotaiClient:
    cfg = get_app_config()
    cred = _to_credentials(acc, cfg)
    return IMaotaiClient(
        cred,
        proxy_pools=cfg.proxy_pools,
        antidetect=cfg.antidetect,
    )


def send_vcode(acc: Account) -> tuple[bool, str]:
    client = client_for_account(acc)
    return client.send_vcode(acc.mobile)


def login_with_vcode(acc: Account, vcode: str) -> tuple[str, str]:
    client = client_for_account(acc)
    token, user_id = client.login(acc.mobile, vcode)
    return token, user_id


def validate_token(acc: Account) -> tuple[bool, str]:
    if not acc.token_enc:
        return False, "未登录"
    client = client_for_account(acc)
    return client.validate_token()


def sync_account_to_credentials_file(acc: Account) -> None:
    """与一期 CLI credentials.json 双向兼容。"""
    cfg = get_app_config()
    cred = _to_credentials(acc, cfg)
    cred.user_id = acc.user_id
    existing = load_credentials(cfg.secret_key)
    rest = [a for a in existing if a.mobile != acc.mobile]
    rest.append(cred)
    save_credentials(rest, cfg.secret_key)


def import_from_credentials_file(db_accounts: list) -> int:
    """从 credentials.json 导入到 DB（启动时）。"""
    cfg = get_app_config()
    try:
        creds = load_credentials(cfg.secret_key)
    except Exception:
        return 0
    existing_mobiles = {a.mobile for a in db_accounts}
    count = 0
    return count  # handled in startup sync


def health_items() -> list[dict]:
    from ..core.database import SessionLocal
    from ..models.entities import Account, Job
    from .scheduler_service import scheduler_status

    report = run_health_check()
    items = [
        {"level": i.level, "category": i.category, "message": i.message}
        for i in report.items
    ]
    db = SessionLocal()
    try:
        total = db.query(Account).count()
        logged = db.query(Account).filter(Account.token_enc != "").count()
        items.append(
            {
                "level": "ok",
                "category": "database",
                "message": f"账号 {total} 个，已登录 {logged} 个",
            }
        )
        running = db.query(Job).filter(Job.status == "running").count()
        if running:
            items.append(
                {
                    "level": "warn",
                    "category": "jobs",
                    "message": f"当前 {running} 个任务执行中",
                }
            )
    finally:
        db.close()
    sched = scheduler_status()
    if sched.get("running"):
        for j in sched.get("jobs", []):
            items.append(
                {
                    "level": "ok",
                    "category": "scheduler",
                    "message": f"{j['id']} 下次运行 {j.get('next_run') or '-'}",
                }
            )
    elif sched.get("enabled"):
        items.append(
            {"level": "warn", "category": "scheduler", "message": "定时任务未运行"}
        )
    else:
        items.append(
            {"level": "warn", "category": "scheduler", "message": "定时任务已关闭"}
        )
    return items


def shop_rank_for_account(acc: Account, item_code: str, limit: int = 10) -> dict:
    from src.shop_selector import rank_shops_for_item

    cfg = get_app_config()
    client = client_for_account(acc)
    client.refresh_session_id()
    p_c_map, shop_details = client.fetch_shop_map()
    shops = client.fetch_session_shops(item_code)
    rank = rank_shops_for_item(
        shops,
        item_code,
        shop_details,
        p_c_map,
        acc.province,
        acc.city,
        cfg.shop_scope,
        limit=limit,
    )
    return {
        "session_id": client.session_id or "0",
        "items": rank,
    }
