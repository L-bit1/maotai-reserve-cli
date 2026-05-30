"""中签查询、周末欢乐购、旅行、统一付款汇总。"""

from __future__ import annotations

import csv
import io
import logging
import time
from datetime import date, datetime
from typing import Callable

from .api import IMaotaiClient, fetch_app_version
from .config_loader import AppConfig, ItemConfig, load_config, load_credentials, mask_mobile, validate_secret_key
from .notify import push_pushplus
from .runner import prepare_account, reserve_one_item

logger = logging.getLogger(__name__)

OnLine = Callable[[str], None] | None


def _emit(on_line: OnLine, msg: str) -> None:
    logger.info(msg)
    if on_line:
        on_line(msg)


def _client_for(acc, cfg: AppConfig) -> IMaotaiClient:
    return IMaotaiClient(
        acc,
        fetch_app_version(),
        proxy_pools=cfg.proxy_pools,
        antidetect=cfg.antidetect,
    )


def sync_lottery_for_account(
    client: IMaotaiClient,
    *,
    today_only: bool = False,
) -> list[dict]:
    """拉取单账号申购/中签结果。"""
    rows = client.query_reservation_results()
    if not today_only:
        return rows
    today = date.today()
    out = []
    for r in rows:
        ts = r.get("reservation_time") or 0
        if ts and datetime.fromtimestamp(ts / 1000).date() == today:
            out.append(r)
    return out


def query_lottery_all(*, today_only: bool = True, on_line: OnLine = None) -> list[dict]:
    """批量查询中签，返回带 mobile 字段的列表。"""
    cfg = load_config()
    validate_secret_key(cfg.secret_key)
    accounts = load_credentials(cfg.secret_key)
    if not accounts:
        raise FileNotFoundError("未配置账号")

    merged: list[dict] = []
    for acc in accounts:
        if not acc.token:
            _emit(on_line, f"⏭ {mask_mobile(acc.mobile)} 未登录，跳过")
            continue
        label = mask_mobile(acc.mobile)
        try:
            client = _client_for(acc, cfg)
            rows = sync_lottery_for_account(client, today_only=today_only)
            for r in rows:
                r["mobile"] = acc.mobile
                r["pay_password_hint"] = bool(acc.pay_password)
            merged.extend(rows)
            won = [x for x in rows if x.get("status") == "won"]
            pending = [x for x in won if x.get("payment_status") == "pending"]
            _emit(
                on_line,
                f"📋 {label} 记录 {len(rows)} 条，中签 {len(won)}，待付款 {len(pending)}",
            )
        except Exception as e:
            _emit(on_line, f"❌ {label} 查询失败: {e}")
        time.sleep(0.3)
    return merged


def pending_payments(rows: list[dict] | None = None) -> list[dict]:
    """待付款清单（中签且 payment_status=pending）。"""
    if rows is None:
        rows = query_lottery_all(today_only=False)
    return [r for r in rows if r.get("status") == "won" and r.get("payment_status") == "pending"]


def notify_pending_payments(rows: list[dict] | None = None) -> None:
    cfg = load_config()
    pending = pending_payments(rows)
    if not pending:
        push_pushplus(cfg.pushplus_token, "i茅台待付款", "当前无待付款中签订单")
        return
    lines = [
        "请在 i茅台 App 内 24 小时内完成支付（本工具无法代付）：",
        "",
    ]
    for p in pending:
        lines.append(
            f"· {mask_mobile(p.get('mobile', ''))} {p.get('item_name', '')} "
            f"[{p.get('session_name', '')}] 订单:{p.get('order_id', '-')}"
        )
    push_pushplus(cfg.pushplus_token, f"i茅台待付款 {len(pending)} 笔", "\n".join(lines))


def export_pending_csv(rows: list[dict] | None = None) -> str:
    cfg = load_config()
    validate_secret_key(cfg.secret_key)
    creds = {c.mobile: c for c in load_credentials(cfg.secret_key)}
    pending = pending_payments(rows)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["手机号", "商品", "场次", "订单号", "支付密码备注", "说明"])
    for p in pending:
        acc = creds.get(p.get("mobile", ""))
        pwd = ""
        if acc and acc.pay_password:
            pwd = "已保存(见本机凭证)"
        w.writerow(
            [
                p.get("mobile", ""),
                p.get("item_name", ""),
                p.get("session_name", ""),
                p.get("order_id", ""),
                pwd,
                "请在 i茅台 App 内支付",
            ],
        )
    return buf.getvalue()


def run_weekend_happy_buy(*, on_line: OnLine = None) -> None:
    """周末欢乐购：与日常商品列表重合的商品才预约。"""
    cfg = load_config()
    validate_secret_key(cfg.secret_key)
    accounts = load_credentials(cfg.secret_key)
    daily_codes = {i.code for i in cfg.items}
    if not daily_codes:
        raise ValueError("config.yaml 未配置商品 items")

    for acc in accounts:
        label = mask_mobile(acc.mobile)
        if not acc.token:
            _emit(on_line, f"⏭ {label} 未登录")
            continue
        try:
            client = _client_for(acc, cfg)
            spec = client.fetch_weekend_special_session()
            session_id = spec["session_id"]
            weekend_codes = {i["item_code"] for i in spec["items"] if i["item_code"]}
            overlap = sorted(daily_codes & weekend_codes)
            if not overlap:
                _emit(on_line, f"⏭ {label} 周末专场与日常商品无重合")
                continue
            _emit(on_line, f"🎉 {label} 周末欢乐购 session={session_id} 商品={overlap}")
            prepare_account(client, cfg, dry_run=False)
            client.session_id = session_id
            p_c_map, shop_details = client.fetch_shop_map()
            strat = (acc.shop_strategy or "").strip() or cfg.shop_strategy
            for code in overlap:
                item_cfg = next((x for x in cfg.items if x.code == code), ItemConfig(code, code))
                ok, line = reserve_one_item(
                    client,
                    cfg,
                    item_cfg,
                    p_c_map,
                    shop_details,
                    strat,
                    dry_run=False,
                )
                _emit(on_line, f"  {'✅' if ok else '❌'} {line}")
        except Exception as e:
            _emit(on_line, f"❌ {label} 周末欢乐购失败: {e}")
        time.sleep(0.5)


def run_travel_all(*, on_line: OnLine = None) -> None:
    cfg = load_config()
    validate_secret_key(cfg.secret_key)
    for acc in load_credentials(cfg.secret_key):
        if not acc.token:
            continue
        label = mask_mobile(acc.mobile)
        try:
            lines = _client_for(acc, cfg).run_travel()
            for ln in lines:
                _emit(on_line, f"🧳 {label} {ln}")
        except Exception as e:
            _emit(on_line, f"❌ {label} 旅行失败: {e}")
