"""统一预约执行：复用 src.runner.execute_reserve（含定时、捡漏波次）。"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.entities import Job
from .credential_sync import sync_db_to_credentials_file

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_scheduled_running = False


def _parse_ids(raw: str) -> list[int]:
    try:
        return [int(x) for x in json.loads(raw or "[]")]
    except Exception:
        return []


def run_reserve_in_background(
    *,
    job_id: int | None = None,
    dry_run: bool = False,
    skip_wait: bool = False,
    account_ids: list[int] | None = None,
    job_name: str = "预约任务",
) -> int | None:
    """后台线程执行完整预约流程。返回 job_id。"""
    db = SessionLocal()
    try:
        if job_id is None:
            job = Job(
                name=job_name,
                job_type="scheduled" if not skip_wait else "manual",
                dry_run=dry_run,
                account_ids_json=json.dumps(account_ids or []),
                product_ids_json="[]",
                status="pending",
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
        else:
            job = db.get(Job, job_id)
            if not job:
                return None
    finally:
        db.close()

    t = threading.Thread(
        target=_execute,
        args=(job_id, dry_run, skip_wait, account_ids),
        daemon=True,
    )
    t.start()
    return job_id


def _execute(
    job_id: int,
    dry_run: bool,
    skip_wait: bool,
    account_ids: list[int] | None,
) -> None:
    global _scheduled_running
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.log_text = "同步账号…\n"
        db.commit()

        n = sync_db_to_credentials_file(db, account_ids=account_ids, require_token=not dry_run)
        if n == 0 and not dry_run:
            job.status = "failed"
            job.log_text = "无已登录账号，请先完成短信登录"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            return

        job.log_text += f"已加载 {n} 个账号，开始预约（skip_wait={skip_wait}）…\n"
        db.commit()

        lines: list[str] = []

        def on_line(line: str) -> None:
            lines.append(line)
            job.log_text = "\n".join(lines[-300:])
            db.commit()

        from src.config_loader import ConfigError
        from src.runner import execute_reserve

        try:
            with _lock:
                if not skip_wait:
                    _scheduled_running = True
                success, all_lines = execute_reserve(
                    dry_run=dry_run,
                    skip_wait=skip_wait,
                    on_line=on_line,
                )
            lines.extend(all_lines)
        except ConfigError as e:
            lines.append(f"❌ {e}")
            success = False
        finally:
            _scheduled_running = False

        ok_count = sum(1 for ln in lines if ln.startswith("✅") or ln.startswith("🔍"))
        if not lines:
            job.status = "failed"
        elif ok_count == len(lines):
            job.status = "success"
        elif ok_count > 0:
            job.status = "partial"
        else:
            job.status = "failed"
        job.progress = 100
        job.log_text = "\n".join(lines[-500:])
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("任务 %s 完成 status=%s", job_id, job.status)
    except Exception as e:
        logger.exception("预约任务 %s 失败: %s", job_id, e)
        try:
            job = db.get(Job, job_id)
            if job:
                job.status = "failed"
                job.log_text = (job.log_text or "") + f"\n❌ {e}"
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def is_scheduled_reserve_running() -> bool:
    return _scheduled_running
