"""预约执行核心逻辑，供 main.py 与 CLI 共用（含龙蒙超版反检测合并）。"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime

from .api import IMaotaiClient, fetch_app_version
from .config_loader import (
    AccountCredentials,
    AntidetectConfig,
    AppConfig,
    ItemConfig,
    load_config,
    load_credentials,
    mask_mobile,
    validate_secret_key,
)
from .exceptions import ConfigError, SessionNotReadyError, TokenExpiredError
from .notify import push_pushplus
from .scheduler import wait_until_clock_time, wait_until_reserve_time

logger = logging.getLogger(__name__)
TODAY = datetime.now().strftime("%Y%m%d")

_SHOP_FAIL_HINTS = ("门店", "店铺", "不参与", "shop", "SHOP")


def _human_delay(min_s: float = 0.3, max_s: float = 1.5) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _should_claim_energy(cfg: AppConfig) -> bool:
    if not cfg.claim_energy:
        return False
    ad = cfg.antidetect
    if not ad.enabled:
        return True
    prob = ad.claim_energy_probability
    if prob >= 1.0:
        return True
    if prob <= 0:
        return False
    return random.random() < prob


def _account_gap(
    cfg: AppConfig,
    idx: int,
    dry_run: bool,
    *,
    prev_group: str,
    curr_group: str,
) -> None:
    if idx <= 0 or dry_run:
        return
    if (
        prev_group
        and curr_group != prev_group
        and cfg.egress_group_stagger_seconds > 0
    ):
        time.sleep(cfg.egress_group_stagger_seconds)
        return
    ad = cfg.antidetect
    if ad.enabled and ad.jitter_seconds > 0:
        time.sleep(random.uniform(0.5, ad.jitter_seconds))
    elif cfg.account_stagger_seconds > 0:
        time.sleep(cfg.account_stagger_seconds)


@dataclass
class ItemAttempt:
    account: AccountCredentials
    item: ItemConfig
    label: str


def _account_strategy(cfg: AppConfig, account: AccountCredentials) -> str:
    return (account.shop_strategy or "").strip() or cfg.shop_strategy


def _needs_shop_fallback(msg: str) -> bool:
    lower = msg.lower()
    return any(h in msg or h.lower() in lower for h in _SHOP_FAIL_HINTS)


def reserve_one_item(
    client: IMaotaiClient,
    cfg: AppConfig,
    item_code: str,
    item_name: str,
    p_c_map: dict,
    shop_details: dict,
    label: str,
    dry_run: bool,
    *,
    strategy: str | None = None,
    fixed_shop_id: str | None = None,
) -> tuple[bool, str]:
    from .shop_selector import rank_shops_for_item, select_shop

    strat = strategy or cfg.shop_strategy
    fixed = (fixed_shop_id or "").strip() or None
    shops = client.fetch_session_shops(item_code)

    shop_id = select_shop(
        strat,
        shops,
        item_code,
        shop_details,
        client.account.province,
        client.account.city,
        p_c_map,
        client.account.lat,
        client.account.lng,
        shop_scope=cfg.shop_scope,
        fixed_shop_id=fixed,
    )
    if not shop_id:
        return False, f"{item_name}: 未找到可预约门店"

    shop_name = shop_details.get(shop_id, {}).get("name", shop_id)

    if dry_run:
        preview = client.preview_reserve(shop_id, item_code)
        rank = rank_shops_for_item(
            shops,
            item_code,
            shop_details,
            p_c_map,
            client.account.province,
            client.account.city,
            cfg.shop_scope,
            limit=5,
        )
        rank_txt = " | ".join(
            f"{r['name'][:8]}({r['inventory']})" for r in rank[:3]
        )
        return True, (
            f"🔍 [试跑] {label} | {item_name} | {shop_name} | "
            f"session={preview['session_id']} actParam={preview['act_param_len']} | "
            f"库存Top: {rank_txt or '无'}"
        )

    last_msg = ""
    tried_fallback = False
    current_shop = shop_id

    for attempt in range(1, cfg.retry_count + 1):
        ok, msg = client.reserve(current_shop, item_code)
        last_msg = msg
        if ok:
            return True, f"✅ {label} | {item_name} | {shop_name} | {msg}"

        if (
            cfg.shop_fallback
            and fixed
            and not tried_fallback
            and _needs_shop_fallback(msg)
        ):
            tried_fallback = True
            alt = select_shop(
                strat,
                shops,
                item_code,
                shop_details,
                client.account.province,
                client.account.city,
                p_c_map,
                client.account.lat,
                client.account.lng,
                shop_scope=cfg.shop_scope,
                fixed_shop_id=None,
            )
            if alt and alt != current_shop:
                current_shop = alt
                shop_name = shop_details.get(alt, {}).get("name", alt)
                logger.info("[%s] 指定门店不可用，改选 %s", item_name, shop_name)
                ok, msg = client.reserve(current_shop, item_code)
                last_msg = msg
                if ok:
                    return True, f"✅ {label} | {item_name} | {shop_name}(换店) | {msg}"

        logger.warning("预约失败 [%s] 第%d次: %s", item_name, attempt, msg)
        if attempt < cfg.retry_count:
            base = cfg.retry_interval
            if cfg.antidetect.enabled:
                time.sleep(max(0.2, base * random.uniform(0.5, 2.0)))
            else:
                time.sleep(base)

    return False, f"❌ {label} | {item_name} | {shop_name} | {last_msg}"


def prepare_account(client: IMaotaiClient, cfg: AppConfig, dry_run: bool) -> None:
    ok, msg = client.validate_token()
    if not ok:
        raise TokenExpiredError(
            f"{mask_mobile(client.account.mobile)}: {msg}，请重新登录"
        )
    logger.info("Token 校验: %s — %s", mask_mobile(client.account.mobile), msg)

    if dry_run:
        sid = client.refresh_session_id()
        if sid == "0":
            logger.warning("试跑: sessionId=0，仍将演示选店与加密")
        return

    client.ensure_session_id(
        max_wait_seconds=cfg.session_wait_seconds,
        poll_interval=cfg.session_poll_interval,
    )


def prewarm_accounts(
    accounts: list[AccountCredentials],
    app_ver: str,
    proxy_pools: dict[str, str] | None = None,
    antidetect: AntidetectConfig | None = None,
) -> None:
    """提前拉取门店映射与场次，减少 9:00 整点接口压力。"""
    logger.info("预热：为 %d 个账号预拉门店与 session…", len(accounts))
    ad = antidetect or AntidetectConfig(enabled=False, warmup_before_reserve=False)
    for acc in accounts:
        if TODAY > acc.end_date:
            continue
        client = IMaotaiClient(
            acc, app_version=app_ver, proxy_pools=proxy_pools, antidetect=ad
        )
        try:
            client.fetch_shop_map()
            sid = client.refresh_session_id()
            logger.info("%s 预热完成 sessionId=%s", mask_mobile(acc.mobile), sid)
        except Exception as e:
            logger.warning("%s 预热失败: %s", mask_mobile(acc.mobile), e)


def run_account(
    client: IMaotaiClient,
    cfg: AppConfig,
    dry_run: bool,
) -> list[tuple[bool, str]]:
    results: list[tuple[bool, str]] = []
    label = mask_mobile(client.account.mobile)
    if not dry_run:
        client.warmup()
    prepare_account(client, cfg, dry_run)
    p_c_map, shop_details = client.fetch_shop_map()

    if _should_claim_energy(cfg) and not dry_run:
        logger.info("小茅运/耐力: %s", client.claim_energy())
    elif cfg.claim_energy and cfg.antidetect.enabled and not dry_run:
        logger.info("本次跳过小茅运/耐力（随机）")

    strat = _account_strategy(cfg, client.account)
    fixed = (client.account.shop_id or "").strip() or None

    for i, item in enumerate(cfg.items):
        if i > 0 and cfg.antidetect.enabled and not dry_run:
            _human_delay(0.5, 2.0)
        ok, line = reserve_one_item(
            client,
            cfg,
            item.code,
            item.name,
            p_c_map,
            shop_details,
            label,
            dry_run,
            strategy=strat,
            fixed_shop_id=fixed,
        )
        results.append((ok, line))
        logger.info(line)
    return results


def _run_pass(
    cfg: AppConfig,
    accounts: list[AccountCredentials],
    app_ver: str,
    dry_run: bool,
    attempts: list[ItemAttempt] | None,
    on_line: callable | None,
) -> tuple[list[str], list[ItemAttempt]]:
    """执行一轮预约；attempts 非空时仅跑列出的账号+商品（捡漏波次）。"""
    all_lines: list[str] = []
    failed: list[ItemAttempt] = []

    if attempts is None:
        work: list[ItemAttempt] = []
        for acc in accounts:
            if TODAY > acc.end_date:
                line = f"跳过过期账号 {mask_mobile(acc.mobile)}"
                all_lines.append(line)
                if on_line:
                    on_line(line)
                continue
            for item in cfg.items:
                work.append(
                    ItemAttempt(
                        account=acc,
                        item=item,
                        label=mask_mobile(acc.mobile),
                    )
                )
    else:
        work = attempts

    prev_group: str | None = None
    prev_mobile: str | None = None
    for idx, task in enumerate(work):
        acc = task.account
        group = (acc.egress_group or "").strip()
        new_account = acc.mobile != prev_mobile
        if idx > 0 and not dry_run and new_account:
            _account_gap(
                cfg,
                idx,
                dry_run,
                prev_group=prev_group or "",
                curr_group=group,
            )
        prev_group = group
        prev_mobile = acc.mobile

        if TODAY > acc.end_date:
            continue

        client = IMaotaiClient(
            acc,
            app_version=app_ver,
            proxy_pools=cfg.proxy_pools,
            antidetect=cfg.antidetect,
        )
        try:
            if not dry_run and attempts is None:
                client.warmup()
            prepare_account(client, cfg, dry_run)
            p_c_map, shop_details = client.fetch_shop_map()
            if _should_claim_energy(cfg) and not dry_run and attempts is None:
                logger.info("小茅运/耐力: %s", client.claim_energy())
            elif cfg.claim_energy and cfg.antidetect.enabled and not dry_run and attempts is None:
                logger.info("%s 跳过小茅运/耐力（随机）", task.label)

            strat = _account_strategy(cfg, acc)
            fixed = (acc.shop_id or "").strip() or None
            ok, line = reserve_one_item(
                client,
                cfg,
                task.item.code,
                task.item.name,
                p_c_map,
                shop_details,
                task.label,
                dry_run,
                strategy=strat,
                fixed_shop_id=fixed,
            )
            all_lines.append(line)
            if on_line:
                on_line(line)
            if not ok and not dry_run:
                failed.append(task)
        except (TokenExpiredError, SessionNotReadyError) as e:
            line = f"❌ {e}"
            all_lines.append(line)
            if on_line:
                on_line(line)
            if not dry_run:
                failed.append(task)
        except Exception as e:
            line = f"❌ {task.label}: {e}"
            logger.exception(line)
            all_lines.append(line)
            if on_line:
                on_line(line)
            if not dry_run:
                failed.append(task)

    return all_lines, failed


def execute_reserve(
    *,
    dry_run: bool = False,
    skip_wait: bool = False,
    on_line: callable | None = None,
) -> tuple[bool, list[str]]:
    """
    执行预约流程（含可选预热、多波次捡漏）。
    返回 (是否整体成功, 结果行列表)
    """
    cfg = load_config()
    validate_secret_key(cfg.secret_key)
    accounts = load_credentials(cfg.secret_key)
    if not accounts:
        raise ConfigError("无账号，请先登录")

    active = [a for a in accounts if TODAY <= a.end_date]
    app_ver = fetch_app_version()
    waves = [] if dry_run or skip_wait else (cfg.schedule.wave_times or [])
    ad = cfg.antidetect
    logger.info(
        "模式: %s | App %s | 策略: %s | 范围: %s | 波次: %s | 反检测: %s",
        "试跑" if dry_run else "正式",
        app_ver,
        cfg.shop_strategy,
        cfg.shop_scope,
        len(waves),
        "开" if ad.enabled else "关",
    )

    if not skip_wait and not dry_run:

        def _prewarm() -> None:
            prewarm_accounts(
                active,
                app_ver,
                cfg.proxy_pools,
                antidetect=AntidetectConfig(
                    enabled=ad.enabled,
                    warmup_before_reserve=False,
                ),
            )

        if cfg.schedule.prewarm_minutes > 0:
            wait_until_reserve_time(cfg.schedule, on_prewarm=_prewarm)
        else:
            wait_until_reserve_time(cfg.schedule)
    elif cfg.schedule.prewarm_minutes > 0 and not dry_run:
        prewarm_accounts(
            active,
            app_ver,
            cfg.proxy_pools,
            antidetect=AntidetectConfig(enabled=ad.enabled, warmup_before_reserve=False),
        )

    all_lines, failed = _run_pass(cfg, active, app_ver, dry_run, None, on_line)
    success_any = any(
        ln.startswith("✅") or ln.startswith("🔍") for ln in all_lines
    )

    pending = failed if cfg.schedule.wave_retry_failed_only else None
    for i, wave_at in enumerate(waves):
        if dry_run:
            break
        wait_until_clock_time(wave_at, label=f"捡漏波次{i + 1}")
        wave_lines, failed = _run_pass(
            cfg,
            active,
            app_ver,
            dry_run,
            pending,
            on_line,
        )
        all_lines.extend(wave_lines)
        if any(ln.startswith("✅") for ln in wave_lines):
            success_any = True
        pending = failed if cfg.schedule.wave_retry_failed_only else None
        if not failed:
            logger.info("捡漏波次 %s：无待重试项，结束", wave_at)
            break

    title = "i茅台试跑完成" if dry_run else (
        "i茅台预约完成" if success_any else "i茅台预约结果"
    )
    push_pushplus(cfg.pushplus_token, title, "\n".join(all_lines))

    return success_any, all_lines
