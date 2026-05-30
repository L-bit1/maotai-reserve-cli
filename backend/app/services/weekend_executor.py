"""后台执行周末欢乐购 / 旅行。"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ..core.database import SessionLocal
from ..models.entities import Account
from .imaotai_service import client_for_account, mask_mobile_api


def run_weekend_async(account_ids: list[int]) -> None:
    threading.Thread(target=_run_weekend, args=(account_ids,), daemon=True).start()


def run_travel_async(account_ids: list[int]) -> None:
    threading.Thread(target=_run_travel, args=(account_ids,), daemon=True).start()


def _run_weekend(account_ids: list[int]) -> None:
    from src.config_loader import ItemConfig, load_config
    from src.runner import prepare_account, reserve_one_item

    cfg = load_config()
    daily_codes = {i.code for i in cfg.items}
    db = SessionLocal()
    try:
        for aid in account_ids:
            acc = db.get(Account, aid)
            if not acc or not acc.enabled or not acc.token_enc:
                continue
            try:
                client = client_for_account(acc)
                spec = client.fetch_weekend_special_session()
                client.session_id = spec["session_id"]
                overlap = sorted(
                    daily_codes & {i["item_code"] for i in spec["items"] if i["item_code"]}
                )
                if not overlap:
                    continue
                prepare_account(client, cfg, dry_run=False)
                p_c_map, shop_details = client.fetch_shop_map()
                strat = (acc.shop_strategy or "").strip() or cfg.shop_strategy
                for code in overlap:
                    item_cfg = next((x for x in cfg.items if x.code == code), ItemConfig(code, code))
                    reserve_one_item(
                        client, cfg, item_cfg, p_c_map, shop_details, strat, dry_run=False
                    )
            except Exception:
                pass
    finally:
        db.close()


def _run_travel(account_ids: list[int]) -> None:
    db = SessionLocal()
    try:
        for aid in account_ids:
            acc = db.get(Account, aid)
            if not acc or not acc.enabled or not acc.token_enc:
                continue
            try:
                client_for_account(acc).run_travel()
            except Exception:
                pass
    finally:
        db.close()
