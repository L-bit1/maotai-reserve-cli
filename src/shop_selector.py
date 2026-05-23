"""门店选择：库存优先 / 低竞争 / 距离优先 / 固定门店。"""

from __future__ import annotations

import math
from typing import Any


def _city_shop_ids(
    province_city_map: dict,
    province: str,
    city: str,
    shop_scope: str,
) -> set[str] | None:
    """shop_scope=city 仅本市；province 全省可预约门店。"""
    if shop_scope == "province":
        prov_map = province_city_map.get(province, {})
        if not prov_map:
            return None
        ids: set[str] = set()
        for shop_list in prov_map.values():
            ids.update(shop_list)
        return ids or None
    prov_map = province_city_map.get(province, {})
    if city in prov_map:
        return set(prov_map[city])
    return None


def _iter_item_shops(
    shops: list[dict],
    item_code: str,
    city_shop_ids: set[str] | None,
) -> list[tuple[str, int]]:
    """返回 [(shop_id, inventory), ...] 仅含可预约该商品且 inventory>0 的店。"""
    out: list[tuple[str, int]] = []
    for shop in shops:
        shop_id = str(shop.get("shopId", ""))
        if city_shop_ids is not None and shop_id not in city_shop_ids:
            continue
        for item in shop.get("items", []):
            if str(item.get("itemId")) != str(item_code):
                continue
            inv = int(item.get("inventory", 0))
            if inv > 0:
                out.append((shop_id, inv))
            break
    return out


def pick_shop_max_inventory(
    shops: list[dict],
    item_code: str,
    city_shop_ids: set[str] | None = None,
) -> str | None:
    """库存最大 — 开源 [ken-iMoutai-Script](https://github.com/AkenClub/ken-iMoutai-Script) INVENTORY 模式。"""
    best_id: str | None = None
    best_inv = -1
    for shop_id, inv in _iter_item_shops(shops, item_code, city_shop_ids):
        if inv > best_inv:
            best_inv = inv
            best_id = shop_id
    return best_id


def pick_shop_min_competition(
    shops: list[dict],
    item_code: str,
    city_shop_ids: set[str] | None = None,
) -> str | None:
    """可预约门店中 inventory 最小（>0）— 参考网易攻略「避开最热门店」。"""
    candidates = _iter_item_shops(shops, item_code, city_shop_ids)
    if not candidates:
        return None
    return min(candidates, key=lambda x: x[1])[0]


def pick_shop_nearest(
    shops: list[dict],
    item_code: str,
    shop_details: dict[str, Any],
    lat: float,
    lng: float,
    city_shop_ids: set[str] | None = None,
) -> str | None:
    best_id: str | None = None
    best_dist = float("inf")
    for shop in shops:
        shop_id = str(shop.get("shopId", ""))
        if city_shop_ids is not None and shop_id not in city_shop_ids:
            continue
        item_ids = [str(i.get("itemId")) for i in shop.get("items", [])]
        if str(item_code) not in item_ids:
            continue
        info = shop_details.get(shop_id) or {}
        slat, slng = float(info.get("lat", 0)), float(info.get("lng", 0))
        dist = math.sqrt((lat - slat) ** 2 + (lng - slng) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_id = shop_id
    return best_id


def rank_shops_for_item(
    shops: list[dict],
    item_code: str,
    shop_details: dict[str, Any],
    province_city_map: dict,
    province: str,
    city: str,
    shop_scope: str = "city",
    limit: int = 8,
) -> list[dict[str, Any]]:
    """按 inventory 降序排行，供试跑/日志参考。"""
    city_ids = _city_shop_ids(province_city_map, province, city, shop_scope)
    rows: list[dict[str, Any]] = []
    for shop_id, inv in _iter_item_shops(shops, item_code, city_ids):
        info = shop_details.get(shop_id) or {}
        rows.append({
            "shop_id": shop_id,
            "name": info.get("name", shop_id),
            "city": info.get("cityName", ""),
            "inventory": inv,
        })
    rows.sort(key=lambda r: r["inventory"], reverse=True)
    return rows[:limit]


def shop_supports_item(shops: list[dict], shop_id: str, item_code: str) -> bool:
    for shop in shops:
        if str(shop.get("shopId")) != str(shop_id):
            continue
        for item in shop.get("items", []):
            if str(item.get("itemId")) == str(item_code):
                return int(item.get("inventory", 0)) > 0
        return False
    return False


def select_shop(
    strategy: str,
    shops: list[dict],
    item_code: str,
    shop_details: dict[str, Any],
    province: str,
    city: str,
    province_city_map: dict,
    lat: str,
    lng: str,
    *,
    shop_scope: str = "city",
    fixed_shop_id: str | None = None,
) -> str | None:
    city_ids = _city_shop_ids(province_city_map, province, city, shop_scope)

    if fixed_shop_id and shop_supports_item(shops, fixed_shop_id, item_code):
        return str(fixed_shop_id)

    if strategy == "nearest":
        return pick_shop_nearest(
            shops, item_code, shop_details, float(lat), float(lng), city_ids
        )
    if strategy == "min_competition":
        return pick_shop_min_competition(shops, item_code, city_ids)
    return pick_shop_max_inventory(shops, item_code, city_ids)
