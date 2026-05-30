"""中签查询与同步。"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import ok
from ...models.entities import Account, LotteryResult
from ...services import imaotai_service
from ...services.imaotai_service import client_for_account, get_app_config, mask_mobile_api
from ...services.lottery_sync_service import sync_all_accounts, upsert_results
from ..deps import get_current_user

router = APIRouter(prefix="/lottery", tags=["中签"])


def _row_out(r: LotteryResult) -> dict:
    return {
        "id": r.id,
        "account_id": r.account_id,
        "mobile": mask_mobile_api(r.mobile),
        "item_id": r.item_id,
        "item_name": r.item_name,
        "session_name": r.session_name,
        "status": r.status,
        "payment_status": r.payment_status,
        "order_id": r.order_id,
        "pay_deadline": r.pay_deadline,
        "reservation_time": r.reservation_time,
        "remark": r.remark,
        "queried_at": r.queried_at.isoformat() if r.queried_at else None,
        "paid_marked_at": r.paid_marked_at.isoformat() if r.paid_marked_at else None,
    }


@router.get("/results")
def list_results(
    status: str | None = Query(None),
    payment_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    q = db.query(LotteryResult).order_by(LotteryResult.id.desc())
    if status:
        q = q.filter(LotteryResult.status == status)
    if payment_status:
        q = q.filter(LotteryResult.payment_status == payment_status)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return ok({"total": total, "items": [_row_out(x) for x in items]})


@router.post("/sync")
def sync_lottery(
    account_ids: list[int] | None = None,
    today_only: bool = True,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    q = db.query(Account).filter(Account.enabled == True)  # noqa: E712
    if account_ids:
        q = q.filter(Account.id.in_(account_ids))
    accounts = q.all()
    synced = 0
    errors: list[str] = []
    for acc in accounts:
        if not acc.token_enc:
            errors.append(f"{mask_mobile_api(acc.mobile)} 未登录")
            continue
        try:
            client = client_for_account(acc)
            rows = client.query_reservation_results()
            if today_only:
                today = date.today()
                rows = [
                    r
                    for r in rows
                    if r.get("reservation_time")
                    and datetime.fromtimestamp(r["reservation_time"] / 1000).date() == today
                ]
            synced += upsert_results(db, acc, rows)
        except Exception as e:
            errors.append(f"{mask_mobile_api(acc.mobile)}: {e}")
    db.commit()
    return ok({"synced": synced, "errors": errors})


@router.post("/weekend-reserve")
def weekend_reserve(
    account_ids: list[int] | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    from ...services.weekend_executor import run_weekend_async

    ids = account_ids or [a.id for a in db.query(Account).filter(Account.enabled == True).all()]  # noqa: E712
    if not ids:
        raise HTTPException(status_code=400, detail={"code": 40001, "message": "无可用账号"})
    run_weekend_async(ids)
    return ok({"message": "周末欢乐购任务已启动", "account_ids": ids})


@router.post("/travel")
def travel_batch(
    account_ids: list[int] | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    from ...services.weekend_executor import run_travel_async

    ids = account_ids or [a.id for a in db.query(Account).filter(Account.enabled == True).all()]  # noqa: E712
    run_travel_async(ids)
    return ok({"message": "旅行任务已启动", "account_ids": ids})
