import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import fail, ok
from ...models.entities import Account
from ...services import imaotai_service
from ...services.imaotai_service import (
    _encrypt_token,
    get_app_config,
    login_with_vcode,
    mask_mobile_api,
    send_vcode,
    validate_token,
)
from src.api import new_device_id
from src.exceptions import AuthError, RateLimitError
from ..deps import get_current_user

router = APIRouter(prefix="/accounts", tags=["账号"])


class AccountCreate(BaseModel):
    mobile: str = Field(min_length=11, max_length=11)
    province: str = ""
    city: str = ""
    lat: str = "28.23"
    lng: str = "112.94"
    receiver_name: str = ""
    receiver_mobile: str = ""
    district: str = ""
    detail_address: str = ""
    shop_strategy: str = ""
    shop_id: str = ""
    egress_group: str = ""
    enabled: bool = True
    end_date: str = "99991231"
    remark: str = ""


class AccountUpdate(BaseModel):
    province: str | None = None
    city: str | None = None
    lat: str | None = None
    lng: str | None = None
    receiver_name: str | None = None
    receiver_mobile: str | None = None
    district: str | None = None
    detail_address: str | None = None
    shop_strategy: str | None = None
    shop_id: str | None = None
    egress_group: str | None = None
    proxy_url: str | None = None
    enabled: bool | None = None
    end_date: str | None = None
    remark: str | None = None


class LoginBody(BaseModel):
    vcode: str


def _acc_out(a: Account) -> dict:
    return {
        "id": a.id,
        "mobile": mask_mobile_api(a.mobile),
        "mobile_raw": a.mobile,
        "user_id": a.user_id,
        "province": a.province,
        "city": a.city,
        "lat": a.lat,
        "lng": a.lng,
        "receiver_name": a.receiver_name,
        "receiver_mobile": a.receiver_mobile,
        "district": a.district,
        "detail_address": a.detail_address,
        "shop_strategy": a.shop_strategy,
        "shop_id": a.shop_id,
        "egress_group": a.egress_group,
        "enabled": a.enabled,
        "end_date": a.end_date,
        "remark": a.remark,
        "logged_at": a.logged_at.isoformat() if a.logged_at else None,
        "last_reserved_at": a.last_reserved_at.isoformat() if a.last_reserved_at else None,
        "last_error": a.last_error,
        "has_token": bool(a.token_enc),
    }


@router.get("")
def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: str | None = Query(None, description="手机号/城市/备注模糊搜索"),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    q = db.query(Account).order_by(Account.id.desc())
    if enabled_only:
        q = q.filter(Account.enabled == True)  # noqa: E712
    if search:
        kw = f"%{search.strip()}%"
        q = q.filter(
            (Account.mobile.like(kw))
            | (Account.city.like(kw))
            | (Account.remark.like(kw))
            | (Account.egress_group.like(kw))
        )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return ok({"total": total, "items": [_acc_out(a) for a in items]})


@router.post("/import-csv")
async def import_accounts_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """批量导入账号（不含 token）。CSV 表头：mobile,province,city,lat,lng,receiver_name,egress_group,shop_strategy,shop_id,remark"""
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gbk", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):
        mobile = (row.get("mobile") or row.get("手机号") or "").strip()
        if len(mobile) != 11:
            skipped += 1
            continue
        acc = db.query(Account).filter(Account.mobile == mobile).first()
        is_new = acc is None
        if is_new:
            acc = Account(mobile=mobile, device_id=new_device_id())
            db.add(acc)
            created += 1
        else:
            updated += 1
        acc.province = (row.get("province") or row.get("省份") or acc.province or "").strip()
        acc.city = (row.get("city") or row.get("城市") or acc.city or "").strip()
        acc.lat = (row.get("lat") or acc.lat or "28.23").strip()
        acc.lng = (row.get("lng") or acc.lng or "112.94").strip()
        acc.receiver_name = (row.get("receiver_name") or row.get("收货人") or acc.receiver_name or "").strip()
        acc.egress_group = (row.get("egress_group") or row.get("出口组") or acc.egress_group or "").strip()
        acc.shop_strategy = (row.get("shop_strategy") or acc.shop_strategy or "").strip()
        acc.shop_id = (row.get("shop_id") or acc.shop_id or "").strip()
        acc.remark = (row.get("remark") or row.get("备注") or acc.remark or "").strip()
        if row.get("enabled", "").lower() in ("0", "false", "否"):
            acc.enabled = False
        elif row.get("enabled"):
            acc.enabled = True
    try:
        db.commit()
        from ...services.credential_sync import sync_db_to_credentials_file

        sync_db_to_credentials_file(db, require_token=True)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=fail(40001, str(e))) from e
    return ok(
        {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:20],
        },
        f"导入完成：新增 {created}，更新 {updated}",
    )


@router.post("/sync-credentials")
def sync_credentials(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    from ...services.credential_sync import sync_db_to_credentials_file

    n = sync_db_to_credentials_file(db)
    return ok({"synced": n}, f"已同步 {n} 个账号到 credentials.json")


@router.get("/export")
def export_accounts(_: str = Depends(get_current_user)):
    from ...services.credential_sync import export_credentials_template

    return ok({"items": export_credentials_template()})


@router.post("")
def create_account(body: AccountCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    if db.query(Account).filter(Account.mobile == body.mobile).first():
        raise HTTPException(status_code=400, detail=fail(40001, "手机号已存在"))
    acc = Account(
        mobile=body.mobile,
        device_id=new_device_id(),
        province=body.province,
        city=body.city,
        lat=body.lat,
        lng=body.lng,
        receiver_name=body.receiver_name,
        receiver_mobile=body.receiver_mobile or body.mobile,
        district=body.district,
        detail_address=body.detail_address,
        shop_strategy=body.shop_strategy,
        shop_id=body.shop_id,
        egress_group=body.egress_group,
        enabled=body.enabled,
        end_date=body.end_date,
        remark=body.remark,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return ok(_acc_out(acc))


@router.get("/{account_id}")
def get_account(account_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    return ok(_acc_out(acc))


@router.put("/{account_id}")
def update_account(
    account_id: int,
    body: AccountUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(acc, k, v)
    db.commit()
    db.refresh(acc)
    return ok(_acc_out(acc))


@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    db.delete(acc)
    db.commit()
    return ok(None, "已删除")


@router.post("/{account_id}/send-vcode")
def api_send_vcode(account_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    try:
        ok_flag, msg = send_vcode(acc)
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=fail(40029, str(e)))
    if not ok_flag:
        raise HTTPException(status_code=400, detail=fail(50001, msg))
    return ok({"message": msg})


@router.post("/{account_id}/login")
def api_login(
    account_id: int,
    body: LoginBody,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    try:
        cfg = get_app_config()
        token, user_id = login_with_vcode(acc, body.vcode)
        acc.token_enc = _encrypt_token(token, cfg.secret_key)
        acc.user_id = user_id
        acc.logged_at = datetime.now(timezone.utc)
        acc.last_error = ""
        from ...services.imaotai_service import _to_credentials

        cred = _to_credentials(acc, cfg)
        acc.device_ua = cred.device_ua
        acc.device_mt_info = cred.device_mt_info
        acc.device_network = cred.device_network
        db.commit()
        imaotai_service.sync_account_to_credentials_file(acc)
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=fail(40029, str(e)))
    except AuthError as e:
        raise HTTPException(status_code=400, detail=fail(40001, str(e)))
    return ok(
        {
            "user_id": acc.user_id,
            "token_valid": True,
            "logged_at": acc.logged_at.isoformat() if acc.logged_at else None,
        }
    )


@router.post("/{account_id}/validate-token")
def api_validate(account_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    valid, msg = validate_token(acc)
    return ok({"valid": valid, "message": msg})


@router.get("/{account_id}/status")
def account_status(account_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    valid, msg = validate_token(acc) if acc.token_enc else (False, "未登录")
    return ok(
        {
            "has_token": bool(acc.token_enc),
            "token_valid": valid,
            "message": msg,
            "last_reserved_at": acc.last_reserved_at.isoformat() if acc.last_reserved_at else None,
            "last_error": acc.last_error,
        }
    )
