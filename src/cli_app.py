"""茅台抢单软件 — Rich 交互式 CLI。"""

from __future__ import annotations

import logging
import secrets
import sys
from datetime import datetime
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .api import fetch_app_version
from .branding import APP_NAME, LOGO, SUBTITLE, set_terminal_title
from .config_loader import (
    CONFIG_PATH,
    CREDENTIALS_PATH,
    load_config,
    load_credentials,
    mask_mobile,
    validate_secret_key,
)
from .exceptions import ConfigError
from .health import run_health_check
from .extras_runner import (
    export_pending_csv,
    notify_pending_payments,
    query_lottery_all,
    run_travel_all,
    run_weekend_happy_buy,
)
from .runner import execute_reserve
from .setup_form import run_account_setup

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "data" / "run.log"

console = Console()


def _ensure_config() -> None:
    """首次运行：生成 config.yaml。"""
    if CONFIG_PATH.exists():
        return
    example = ROOT / "config.example.yaml"
    if example.exists():
        CONFIG_PATH.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        console.print(f"[yellow]已生成 {CONFIG_PATH.name}[/]")


def _ensure_secret_key() -> None:
    try:
        cfg = load_config()
        validate_secret_key(cfg.secret_key)
    except ConfigError:
        console.print(Panel(
            "[bold]首次使用[/] 请设置本机加密密钥（任意随机字符串，用于保护账号文件）",
            title=APP_NAME,
            border_style="cyan",
        ))
        key = secrets.token_urlsafe(24)
        suggested = Prompt.ask("secret_key", default=key)
        text = CONFIG_PATH.read_text(encoding="utf-8")
        if "请改成你自己的随机字符串" in text:
            text = text.replace("请改成你自己的随机字符串", suggested)
        else:
            import re

            text = re.sub(
                r'^secret_key:\s*".*"',
                f'secret_key: "{suggested}"',
                text,
                count=1,
                flags=re.MULTILINE,
            )
        CONFIG_PATH.write_text(text, encoding="utf-8")
        console.print("[green]secret_key 已写入 config.yaml[/]")


def _banner() -> None:
    from rich.align import Align
    from rich.text import Text

    logo_text = (
        LOGO
        + f"\n[bold white on red]  {APP_NAME}  [/][bold yellow]  🍶 i茅台  [/]\n"
        + SUBTITLE
    )
    console.print(
        Panel(
            Align.center(Text.from_markup(logo_text)),
            border_style="red",
            box=box.DOUBLE_EDGE,
            padding=(0, 1),
        )
    )


def _status_table() -> Table:
    table = Table(
        title=f"{APP_NAME} · 状态",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold red",
    )
    table.add_column("项目", style="cyan", width=12)
    table.add_column("状态", width=44)

    try:
        cfg = load_config()
        validate_secret_key(cfg.secret_key)
        table.add_row("配置", f"[green]✓[/] {len(cfg.items)} 商品 · {cfg.shop_strategy}")
    except Exception as e:
        table.add_row("配置", f"[red]✗[/] {e}")

    try:
        cfg = load_config()
        validate_secret_key(cfg.secret_key)
        accs = load_credentials(cfg.secret_key)
        if accs:
            for a in accs:
                addr = f"{a.province}{a.city}{a.district} {a.detail_address[:20]}…" if a.detail_address else "未填地址"
                table.add_row(
                    "i茅台账号",
                    f"[green]{mask_mobile(a.mobile)}[/]\n[dim]{a.receiver_name} · {addr}[/]",
                )
        else:
            table.add_row("i茅台账号", "[yellow]未配置 · 请选菜单 1[/]")
    except Exception:
        table.add_row("i茅台账号", "[yellow]未配置[/]")

    try:
        table.add_row("App 版本", f"[green]{fetch_app_version()}[/]")
    except Exception:
        table.add_row("App 版本", "[red]—[/]")

    try:
        import datetime as dt
        import time

        import requests

        day_ms = int(time.mktime(dt.date.today().timetuple()) * 1000)
        r = requests.get(
            f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/"
            f"index/session/get/{day_ms}",
            timeout=10,
        )
        sid = r.json().get("data", {}).get("sessionId")
        if sid and str(sid) != "0":
            table.add_row("申购场次", f"[green]session {sid}[/]")
        else:
            table.add_row("申购场次", "[yellow]未开放 (约 9:00–10:00)[/]")
    except Exception:
        pass

    table.add_row("时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return table


def _menu() -> str:
    options = [
        ("1", "账号 / 地址 / 登录", "手机号、验证码、收货地址、支付密码"),
        ("2", "试跑预约", "不提交，仅测试"),
        ("3", "定时正式预约", "等到 8:59:58 提交"),
        ("4", "立即正式预约", "跳过等待"),
        ("5", "健康检查", ""),
        ("6", "查看配置", ""),
        ("7", "运行日志", ""),
        ("8", "查询中签 / 待付款", "18:00 后查询，汇总待付"),
        ("9", "周末欢乐购预约", "周日专场，与日常商品重合才约"),
        ("10", "小茅运旅行", "领取奖励并开始旅行"),
        ("0", "退出", ""),
    ]
    t = Table(box=None, show_header=False, padding=(0, 1))
    t.add_column("", style="bold yellow", width=3)
    t.add_column(style="white", width=18)
    t.add_column(style="dim")
    for k, a, b in options:
        t.add_row(k, a, b)
    console.print(Panel(t, title="主菜单", border_style="blue"))
    return Prompt.ask("[bold red]茅台抢单软件[/] 请选择", choices=[o[0] for o in options], default="1")


def _action_health() -> None:
    with console.status("[green]检查中…[/]"):
        report = run_health_check()
    t = Table(box=box.SIMPLE)
    t.add_column("类", width=6)
    t.add_column("结果", width=48)
    icons = {"ok": "[green]✓[/]", "warn": "[yellow]![/]", "fail": "[red]✗[/]"}
    for item in report.items:
        t.add_row(item.category, f"{icons[item.level]} {item.message}")
    console.print(t)


def _action_setup() -> None:
    try:
        cfg = load_config()
        validate_secret_key(cfg.secret_key)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        return
    if not cfg.amap_key:
        console.print(
            "[yellow]提示: config.yaml 未填 amap_key 时，需手动输入省市区。[/]\n"
            "填写高德 Key 后可搜索小区自动定位。\n"
        )
    run_account_setup(cfg)


def _action_reserve(*, dry_run: bool, skip_wait: bool) -> None:
    if not dry_run and not skip_wait:
        try:
            cfg = load_config()
            console.print(
                f"[yellow]将在 {cfg.schedule.target_time} 前 "
                f"{cfg.schedule.advance_seconds}s 提交[/]"
            )
            if not Confirm.ask("继续?", default=True):
                return
        except Exception:
            pass

    def on_line(line: str) -> None:
        c = "green" if "✅" in line or "🔍" in line else ("red" if "❌" in line else "white")
        console.print(f"  [{c}]{line}[/]")

    try:
        with console.status("[bold green]执行中…[/]"):
            execute_reserve(dry_run=dry_run, skip_wait=skip_wait, on_line=on_line)
    except (FileNotFoundError, ConfigError) as e:
        console.print(f"[red]{e}[/]\n请先选 [1] 配置账号与地址[/]")


def _action_config() -> None:
    from .config_loader import load_config

    cfg = load_config()
    t = Table(title="系统配置", box=box.ROUNDED)
    t.add_column("项", style="cyan")
    t.add_column("值")
    t.add_row("定时", f"{cfg.schedule.target_time} 前 {cfg.schedule.advance_seconds}s")
    t.add_row("策略", cfg.shop_strategy)
    for item in cfg.items:
        t.add_row("商品", f"{item.code} {item.name}")
    console.print(t)


def _action_lottery() -> None:
    def on_line(line: str) -> None:
        c = "green" if "中签" in line or "待付款" in line else "white"
        console.print(f"  [{c}]{line}[/]")

    try:
        with console.status("[bold green]查询申购结果…[/]"):
            rows = query_lottery_all(today_only=Confirm.ask("仅查今日?", default=True), on_line=on_line)
        pending = [r for r in rows if r.get("status") == "won" and r.get("payment_status") == "pending"]
        console.print(f"\n[bold]待付款 {len(pending)} 笔[/]（须在 i茅台 App 内支付）")
        if pending and Confirm.ask("PushPlus 推送待付款清单?", default=bool(load_config().pushplus_token)):
            notify_pending_payments(rows)
        if pending and Confirm.ask("导出 CSV?", default=False):
            path = ROOT / "data" / "pending_payments.csv"
            path.write_text(export_pending_csv(rows), encoding="utf-8-sig")
            console.print(f"[green]已写入 {path}[/]")
    except Exception as e:
        console.print(f"[red]{e}[/]")


def _action_weekend() -> None:
    def on_line(line: str) -> None:
        console.print(f"  {line}")

    try:
        with console.status("[bold green]周末欢乐购…[/]"):
            run_weekend_happy_buy(on_line=on_line)
    except Exception as e:
        console.print(f"[red]{e}[/]")


def _action_travel() -> None:
    def on_line(line: str) -> None:
        console.print(f"  {line}")

    try:
        with console.status("[bold green]旅行任务…[/]"):
            run_travel_all(on_line=on_line)
    except Exception as e:
        console.print(f"[red]{e}[/]")


def _action_logs() -> None:
    if not LOG_FILE.exists():
        console.print("[yellow]暂无日志[/]")
        return
    tail = "\n".join(LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-35:])
    console.print(Panel(tail, title="运行日志", border_style="dim"))


def _dispatch(key: str) -> bool:
    if key == "0":
        return False
    actions = {
        "1": _action_setup,
        "2": lambda: _action_reserve(dry_run=True, skip_wait=True),
        "3": lambda: _action_reserve(dry_run=False, skip_wait=False),
        "4": lambda: _action_reserve(dry_run=False, skip_wait=True),
        "5": _action_health,
        "6": _action_config,
        "7": _action_logs,
        "8": _action_lottery,
        "9": _action_weekend,
        "10": _action_travel,
    }
    fn = actions.get(key)
    if fn:
        fn()
        Prompt.ask("\n[dim]回车返回主菜单[/]", default="")
    return True


class CliApp:
    def run_loop(self) -> None:
        logging.getLogger().setLevel(logging.WARNING)
        set_terminal_title(APP_NAME)
        _ensure_config()
        _ensure_secret_key()

        while True:
            console.clear()
            set_terminal_title(APP_NAME)
            _banner()
            console.print(_status_table())
            if not _dispatch(_menu()):
                console.print(Panel("[dim]感谢使用 茅台抢单软件[/]", border_style="red"))
                break


def run_interactive() -> None:
    CliApp().run_loop()
