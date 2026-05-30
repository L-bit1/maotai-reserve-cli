"""手机 App 便捷接口（单甲方、多账号）。"""

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import ok
from ...models.entities import Account, Job, Product
from ...services.job_executor import run_job_async
from ...services.scheduler_service import scheduler_status
from ..deps import get_current_user

router = APIRouter(prefix="/mobile", tags=["手机端"])


class QuickJobBody(BaseModel):
    name: str = "每日自动预约"
    dry_run: bool = False
    wait_until_reserve: bool = False


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    total_acc = db.query(Account).count()
    logged = db.query(Account).filter(Account.token_enc != "").count()
    enabled = db.query(Account).filter(Account.enabled == True).count()  # noqa: E712
    products = db.query(Product).filter(Product.enabled == True).count()  # noqa: E712
    last_job = db.query(Job).order_by(Job.id.desc()).first()
    sched = scheduler_status()
    return ok(
        {
            "accounts_total": total_acc,
            "accounts_logged_in": logged,
            "accounts_enabled": enabled,
            "products_enabled": products,
            "scheduler": sched,
            "last_job": {
                "id": last_job.id,
                "name": last_job.name,
                "status": last_job.status,
                "progress": last_job.progress,
            }
            if last_job
            else None,
        }
    )


@router.post("/quick-reserve")
def quick_reserve(
    body: QuickJobBody,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """为全部已启用账号 + 已启用商品创建并启动预约任务。"""
    job = Job(
        name=body.name,
        job_type="daily_wait" if body.wait_until_reserve else "daily",
        dry_run=body.dry_run,
        account_ids_json="[]",
        product_ids_json="[]",
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    run_job_async(job.id)
    return ok({"job_id": job.id, "message": "预约任务已启动"})
