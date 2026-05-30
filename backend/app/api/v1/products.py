from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.response import fail, ok
from ...models.entities import Product
from ..deps import get_current_user

router = APIRouter(prefix="/products", tags=["商品"])


class ProductBody(BaseModel):
    item_code: str
    name: str
    enabled: bool = True
    sort_order: int = 0


@router.get("")
def list_products(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    items = db.query(Product).order_by(Product.sort_order, Product.id).all()
    return ok(
        [
            {
                "id": p.id,
                "item_code": p.item_code,
                "name": p.name,
                "enabled": p.enabled,
                "sort_order": p.sort_order,
            }
            for p in items
        ]
    )


@router.post("")
def create_product(body: ProductBody, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    if db.query(Product).filter(Product.item_code == body.item_code).first():
        raise HTTPException(status_code=400, detail=fail(40001, "商品编码已存在"))
    p = Product(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return ok({"id": p.id, **body.model_dump()})


@router.put("/{product_id}")
def update_product(
    product_id: int,
    body: ProductBody,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail=fail(40001, "商品不存在"))
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    db.commit()
    return ok(None)


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail=fail(40001, "商品不存在"))
    p.enabled = False
    db.commit()
    return ok(None, "已软删除")
