from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import fail, ok
from ...models.entities import Account
from ...services.imaotai_service import client_for_account, shop_rank_for_account
from ..deps import get_current_user

router = APIRouter(prefix="/shops", tags=["门店"])


@router.get("/rank")
def shops_rank(
    account_id: int = Query(...),
    item_code: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    if not acc.token_enc:
        raise HTTPException(status_code=400, detail=fail(40001, "账号未登录"))
    try:
        data = shop_rank_for_account(acc, item_code, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=fail(50001, str(e)))
    return ok(data)


@router.post("/sync")
def shops_sync(
    account_id: int = Query(...),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=fail(40001, "账号不存在"))
    client = client_for_account(acc)
    p_c_map, shops = client.fetch_shop_map()
    return ok({"provinces": len(p_c_map), "shops": len(shops)})
