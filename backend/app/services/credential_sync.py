"""数据库账号与 credentials.json 同步（以数据库为准）。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.entities import Account
from .imaotai_service import _to_credentials, get_app_config

logger = logging.getLogger(__name__)


def sync_db_to_credentials_file(
    db: Session | None = None,
    *,
    account_ids: list[int] | None = None,
    require_token: bool = True,
) -> int:
    """将 DB 中启用账号写入 credentials.json，供 execute_reserve 使用。"""
    from src.config_loader import save_credentials

    cfg = get_app_config()
    own = db is None
    if own:
        db = SessionLocal()
    try:
        q = db.query(Account).filter(Account.enabled == True)  # noqa: E712
        if account_ids:
            q = q.filter(Account.id.in_(account_ids))
        accounts = q.order_by(Account.id).all()
        creds = []
        for acc in accounts:
            if require_token and not acc.token_enc:
                continue
            try:
                creds.append(_to_credentials(acc, cfg))
            except Exception as e:
                logger.warning("跳过账号 %s: %s", acc.mobile, e)
        save_credentials(creds, cfg.secret_key)
        logger.info("已同步 %d 个账号到 credentials.json", len(creds))
        return len(creds)
    finally:
        if own and db is not None:
            db.close()


def export_credentials_template() -> list[dict]:
    """导出账号列表（不含 token 明文）。"""
    db = SessionLocal()
    try:
        rows = db.query(Account).order_by(Account.id).all()
        return [
            {
                "mobile": a.mobile,
                "province": a.province,
                "city": a.city,
                "lat": a.lat,
                "lng": a.lng,
                "receiver_name": a.receiver_name,
                "shop_strategy": a.shop_strategy,
                "shop_id": a.shop_id,
                "egress_group": a.egress_group,
                "enabled": a.enabled,
                "has_token": bool(a.token_enc),
            }
            for a in rows
        ]
    finally:
        db.close()
