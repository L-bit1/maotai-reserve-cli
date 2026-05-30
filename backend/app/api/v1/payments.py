"""统一付款管理：待付款汇总、标记已付、导出、提醒。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import ok
from ...models.entities import LotteryResult
from ...services.imaotai_service import get_app_config, mask_mobile_api
from ..deps import get_current_user

router = APIRouter(prefix="/payments", tags=["付款"])


@router.get("/pending")
def pending_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    q = (
        db.query(LotteryResult)
        .filter(LotteryResult.status == "won", LotteryResult.payment_status == "pending")
        .order_by(LotteryResult.id.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return ok(
        {
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "mobile": mask_mobile_api(r.mobile),
                    "item_name": r.item_name,
                    "session_name": r.session_name,
                    "order_id": r.order_id,
                    "pay_deadline": r.pay_deadline,
                    "remark": r.remark,
                }
                for r in items
            ],
            "notice": "请在 i茅台 App 内完成支付；本系统仅汇总待付款订单，无法代扣。",
        }
    )


@router.post("/{result_id}/mark-paid")
def mark_paid(
    result_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    row = db.get(LotteryResult, result_id)
    if not row:
        return ok({"ok": False, "message": "记录不存在"})
    row.payment_status = "paid"
    row.paid_marked_at = datetime.now(timezone.utc)
    db.commit()
    return ok({"ok": True, "id": result_id})


@router.get("/export")
def export_pending(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    rows = (
        db.query(LotteryResult)
        .filter(LotteryResult.status == "won", LotteryResult.payment_status == "pending")
        .all()
    )
    lines = ["手机号,商品,场次,订单号,付款状态,说明"]
    for r in rows:
        lines.append(
            f"{r.mobile},{r.item_name},{r.session_name},{r.order_id},待付款,请在i茅台App内支付"
        )
    body = "\n".join(lines) + "\n"
    return PlainTextResponse(body, media_type="text/csv; charset=utf-8")


@router.post("/notify")
def notify_pending(_: str = Depends(get_current_user)):
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from src.extras_runner import notify_pending_payments, query_lottery_all

    rows = query_lottery_all(today_only=False)
    notify_pending_payments(rows)
    cfg = get_app_config()
    pending = [r for r in rows if r.get("status") == "won" and r.get("payment_status") == "pending"]
    return ok(
        {
            "pushed": bool(cfg.pushplus_token),
            "pending_count": len(pending),
            "message": "已尝试 PushPlus 推送（若已配置 token）",
        }
    )
