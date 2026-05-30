from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import ok
from ...models.entities import ReserveRecord
from ..deps import get_current_user

router = APIRouter(prefix="/records", tags=["预约记录"])


@router.get("")
def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    account_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    q = db.query(ReserveRecord).order_by(ReserveRecord.id.desc())
    if account_id:
        q = q.filter(ReserveRecord.account_id == account_id)
    if status:
        q = q.filter(ReserveRecord.status == status)
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return ok(
        {
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "job_id": r.job_id,
                    "account_id": r.account_id,
                    "item_code": r.item_code,
                    "item_name": r.item_name,
                    "shop_id": r.shop_id,
                    "shop_name": r.shop_name,
                    "session_id": r.session_id,
                    "status": r.status,
                    "message": r.message[:200],
                    "reserved_at": r.reserved_at.isoformat() if r.reserved_at else None,
                }
                for r in rows
            ],
        }
    )


@router.get("/stats")
def records_stats(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    total = db.query(ReserveRecord).count()
    success = db.query(ReserveRecord).filter(ReserveRecord.status == "success").count()
    rate = round(success / total, 3) if total else 0
    return ok(
        {
            "total_attempts": total,
            "submit_success": success,
            "submit_success_rate": rate,
            "by_day": [],
        }
    )


@router.get("/export")
def export_records(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    rows = db.query(ReserveRecord).order_by(ReserveRecord.id.desc()).limit(5000).all()
    lines = ["id,account_id,item_code,status,message,reserved_at"]
    for r in rows:
        lines.append(
            f"{r.id},{r.account_id},{r.item_code},{r.status},"
            f"\"{(r.message or '')[:80]}\",{r.reserved_at}"
        )
    return PlainTextResponse("\n".join(lines), media_type="text/csv")
