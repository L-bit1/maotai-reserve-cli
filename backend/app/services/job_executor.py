"""后台执行预约任务（统一走 reserve_service + execute_reserve）。"""

from __future__ import annotations

import json
import threading

from ..core.database import SessionLocal
from ..models.entities import Job
from .reserve_service import _execute

_running: set[int] = set()
_lock = threading.Lock()


def _parse_ids(raw: str) -> list[int]:
    try:
        return [int(x) for x in json.loads(raw or "[]")]
    except Exception:
        return []


def _skip_wait_for_job(job: Job) -> bool:
    """定时/scheduled 类型等待到 9 点；手动与试跑立即执行。"""
    return job.job_type not in ("scheduled", "daily_wait")


def run_job_async(job_id: int) -> None:
    with _lock:
        if job_id in _running:
            return
        _running.add(job_id)

    t = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    t.start()


def _run_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        account_ids = _parse_ids(job.account_ids_json) or None
        skip_wait = _skip_wait_for_job(job)
        dry_run = job.dry_run
    finally:
        db.close()

    try:
        _execute(job_id, dry_run, skip_wait, account_ids)
    finally:
        with _lock:
            _running.discard(job_id)
