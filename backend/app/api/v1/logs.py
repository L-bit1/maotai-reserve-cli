from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import ok
from ...models.entities import Job
from ..deps import get_current_user

router = APIRouter(prefix="/logs", tags=["日志"])


@router.get("/runtime")
def runtime_logs(_: str = Depends(get_current_user)):
    return ok({"lines": ["管理后端运行中", "查看任务详情获取单次执行日志"]})


@router.get("/jobs/{job_id}")
def job_logs(job_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job:
        from fastapi import HTTPException
        from ...core.response import fail

        raise HTTPException(status_code=404, detail=fail(40001, "任务不存在"))
    return ok({"log_text": job.log_text or ""})
