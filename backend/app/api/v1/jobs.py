import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import fail, ok
from ...models.entities import Job
from ...services.job_executor import run_job_async
from ..deps import get_current_user

router = APIRouter(prefix="/jobs", tags=["任务"])


class JobCreate(BaseModel):
    name: str
    type: str = "manual"
    cron: str = ""
    account_ids: list[int] = []
    product_ids: list[int] = []
    dry_run: bool = False
    wait_until_reserve: bool = False


def _job_out(j: Job) -> dict:
    return {
        "id": j.id,
        "name": j.name,
        "type": j.job_type,
        "cron": j.cron,
        "status": j.status,
        "dry_run": j.dry_run,
        "account_ids": json.loads(j.account_ids_json or "[]"),
        "product_ids": json.loads(j.product_ids_json or "[]"),
        "progress": j.progress,
        "total": j.total,
        "log_preview": (j.log_text or "")[-500:],
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    }


@router.get("")
def list_jobs(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    jobs = db.query(Job).order_by(Job.id.desc()).limit(50).all()
    return ok([_job_out(j) for j in jobs])


@router.post("")
def create_job(body: JobCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    jtype = "daily_wait" if body.wait_until_reserve else body.type
    job = Job(
        name=body.name,
        job_type=jtype,
        cron=body.cron,
        dry_run=body.dry_run,
        account_ids_json=json.dumps(body.account_ids),
        product_ids_json=json.dumps(body.product_ids),
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return ok(_job_out(job))


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=fail(40001, "任务不存在"))
    out = _job_out(job)
    out["log_text"] = job.log_text
    return ok(out)


@router.post("/{job_id}/run")
def run_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=fail(40001, "任务不存在"))
    if job.status == "running":
        raise HTTPException(status_code=400, detail=fail(40001, "任务正在执行"))
    run_job_async(job_id)
    return ok({"message": "已启动", "job_id": job_id})


@router.post("/{job_id}/cancel")
def cancel_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=fail(40001, "任务不存在"))
    if job.status in ("pending", "running"):
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    return ok(None)


@router.post("/dry-run")
def dry_run_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    body.dry_run = True
    body.name = body.name or "试跑"
    return create_job(body, db, user)
