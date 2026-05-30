"""中签结果批量同步。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.entities import Account, LotteryResult
from .imaotai_service import client_for_account, get_app_config

logger = logging.getLogger(__name__)


def upsert_results(db: Session, acc: Account, rows: list[dict]) -> int:
    n = 0
    for r in rows:
        item_id = r.get("item_id", "")
        res_time = int(r.get("reservation_time") or 0)
        existing = (
            db.query(LotteryResult)
            .filter(
                LotteryResult.account_id == acc.id,
                LotteryResult.item_id == item_id,
                LotteryResult.reservation_time == res_time,
            )
            .first()
        )
        if existing is None:
            existing = LotteryResult(account_id=acc.id, item_id=item_id, reservation_time=res_time)
            db.add(existing)
        existing.mobile = acc.mobile
        existing.item_name = r.get("item_name", "")
        existing.session_name = r.get("session_name", "")
        existing.status = r.get("status", "unknown")
        existing.payment_status = r.get("payment_status", "none")
        existing.order_id = r.get("order_id", "")
        existing.pay_deadline = str(r.get("pay_deadline", ""))
        existing.queried_at = datetime.now(timezone.utc)
        n += 1
    return n


def sync_all_accounts() -> tuple[int, int, list[str]]:
    """返回 (synced_rows, pending_payments, errors)。"""
    db = SessionLocal()
    synced = 0
    pending = 0
    errors: list[str] = []
    try:
        accounts = db.query(Account).filter(Account.enabled == True, Account.token_enc != "").all()  # noqa: E712
        for acc in accounts:
            try:
                client = client_for_account(acc)
                rows = client.query_reservation_results()
                synced += upsert_results(db, acc, rows)
                pending += sum(
                    1
                    for r in rows
                    if r.get("status") == "won" and r.get("payment_status") == "pending"
                )
            except Exception as e:
                msg = f"{acc.mobile}: {e}"
                errors.append(msg)
                logger.warning("中签同步失败 %s", msg)
        db.commit()
        cfg = get_app_config()
        if cfg.pushplus_token and pending > 0:
            from src.notify import push_pushplus

            push_pushplus(
                cfg.pushplus_token,
                f"i茅台待付款 {pending} 笔",
                f"已同步 {synced} 条记录，请打开 i茅台 App 完成付款。",
            )
    finally:
        db.close()
    return synced, pending, errors
