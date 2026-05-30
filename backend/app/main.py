"""FastAPI 管理后端入口。"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from .api.v1.router import api_router
from .core.config import settings
from .core.database import SessionLocal, init_db
from .core.response import fail, ok
from .models.entities import Account, Product
from .services.imaotai_service import _encrypt_token, get_app_config

logger = logging.getLogger(__name__)


def _sync_credentials_to_db():
    """启动时把 credentials.json 同步到 SQLite。"""
    try:
        from src.config_loader import load_credentials
        from src.api import new_device_id

        cfg = get_app_config()
        creds = load_credentials(cfg.secret_key)
    except Exception:
        return
    db = SessionLocal()
    try:
        for c in creds:
            acc = db.query(Account).filter(Account.mobile == c.mobile).first()
            if acc is None:
                acc = Account(
                    mobile=c.mobile,
                    device_id=c.device_id or new_device_id(),
                    province=c.province,
                    city=c.city,
                    lat=c.lat,
                    lng=c.lng,
                    receiver_name=c.receiver_name,
                    receiver_mobile=c.receiver_mobile,
                    district=c.district,
                    detail_address=c.detail_address,
                    shop_strategy=c.shop_strategy,
                    shop_id=c.shop_id,
                    egress_group=c.egress_group,
                    proxy_url=c.proxy_url,
                    device_ua=c.device_ua,
                    device_mt_info=c.device_mt_info,
                    device_network=c.device_network,
                )
                db.add(acc)
            if c.token and acc:
                acc.token_enc = _encrypt_token(c.token, cfg.secret_key)
                acc.user_id = c.user_id
        db.commit()
        if not db.query(Product).count() and cfg.items:
            for i, item in enumerate(cfg.items):
                db.add(
                    Product(
                        item_code=item.code,
                        name=item.name,
                        enabled=True,
                        sort_order=i,
                    )
                )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _sync_credentials_to_db()
    from .services.scheduler_service import start_scheduler

    start_scheduler()
    yield
    from .services.scheduler_service import stop_scheduler

    stop_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content=fail(40001, str(exc.errors())))


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(50000, str(detail)),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.exception("未处理异常: %s", exc)
    return JSONResponse(status_code=500, content=fail(50000, str(exc)))


@app.get("/")
def root():
    return {"app": settings.app_name, "docs": "/docs", "api": settings.api_prefix}


@app.get(f"{settings.api_prefix}/ping")
def ping():
    """前端用于检测后端是否已启动（无需登录）。"""
    return ok({"status": "up"})
