"""CLI 账号、登录、收货地址填写表单。"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .api import IMaotaiClient, new_device_id
from .config_loader import (
    AccountCredentials,
    AppConfig,
    load_credentials,
    mask_mobile,
    save_credentials,
)
from .exceptions import AuthError, RateLimitError
from .geocode import geocode_address

console = Console()


def _pick_address(
    cfg: AppConfig,
    *,
    default_name: str = "",
    default_mobile: str = "",
) -> tuple[str, str, str, str, str, str, str, str]:
    """province, city, district, detail, lat, lng, receiver_name, receiver_mobile"""
    console.print("\n[bold cyan]━━━ 收货地址 ━━━[/]")
    console.print(
        "[dim]用于匹配附近门店；中签后提货/配送以 i茅台 App 内地址为准。[/]\n"
    )

    receiver_name = Prompt.ask("收货人姓名", default=default_name)
    receiver_mobile = Prompt.ask("收货人手机", default=default_mobile)

    if cfg.amap_key:
        keyword = Prompt.ask("小区 / 街道 / 地标（可搜索）", default="")
        if keyword.strip():
            geocodes = geocode_address(cfg.amap_key, keyword.strip())
            if geocodes:
                for i, g in enumerate(geocodes):
                    console.print(
                        f"  [yellow]{i}[/] {g.get('province')}{g.get('city')}"
                        f"{g.get('district', '')} {g.get('formatted_address')}"
                    )
                idx = int(Prompt.ask("选择地址序号", default="0"))
                g = geocodes[idx]
                lng, lat = g["location"].split(",")
                return (
                    str(g.get("province", "")),
                    str(g.get("city", "")),
                    str(g.get("district", "")),
                    str(g.get("formatted_address", keyword)),
                    lat,
                    lng,
                    receiver_name,
                    receiver_mobile or default_mobile,
                )
            console.print("[yellow]未匹配到，请手动填写[/]")

    province = Prompt.ask("省份", default="")
    city = Prompt.ask("城市", default="")
    district = Prompt.ask("区/县", default="")
    detail = Prompt.ask("详细地址（街道门牌）", default="")
    lat = Prompt.ask("纬度 lat", default="28.23")
    lng = Prompt.ask("经度 lng", default="112.94")
    return (
        province,
        city,
        district,
        detail,
        lat,
        lng,
        receiver_name,
        receiver_mobile or default_mobile,
    )


def run_account_setup(cfg: AppConfig) -> None:
    console.print(
        Panel(
            "[bold]i茅台 使用「手机号 + 短信验证码」登录[/]\n"
            "· 登录账号 = 11 位手机号\n"
            "· 无网页密码；验证码将发到该手机\n"
            "· 「支付密码」可选，仅本机加密保存，供中签付款时参考",
            title="i茅台 登录说明",
            border_style="yellow",
        )
    )

    console.print("\n[bold cyan]━━━ i茅台 账号 ━━━[/]")
    mobile = Prompt.ask("手机号（登录账号）")
    if len(mobile) != 11 or not mobile.isdigit():
        console.print("[red]手机号须为 11 位数字[/]")
        return

    existing = load_credentials(cfg.secret_key)
    old = next((a for a in existing if a.mobile == mobile), None)
    device_id = old.device_id if old else new_device_id()

    placeholder = AccountCredentials(
        mobile=mobile,
        token=old.token if old else "",
        user_id=old.user_id if old else "0",
        province=old.province if old else "",
        city=old.city if old else "",
        lat=old.lat if old else "28.23",
        lng=old.lng if old else "112.94",
        device_id=device_id,
    )
    client = IMaotaiClient(placeholder, proxy_pools=cfg.proxy_pools)

    if old and old.token and Confirm.ask("已有登录，是否重新获取短信验证码登录?", default=False):
        token, user_id = old.token, old.user_id
        console.print("[dim]沿用已保存登录[/]")
    else:
        if not Confirm.ask("向该手机号发送短信验证码?", default=True):
            return
        with console.status("[green]发送验证码…[/]"):
            ok, msg = client.send_vcode(mobile)
        if not ok:
            console.print(Panel(f"[red]{msg}[/]", title="发送失败", border_style="red"))
            return
        console.print(f"[green]{msg}[/]")
        console.print("[dim]收到短信后再输入；勿重复发送，否则易触发 429 限流。[/]")

        vcode = Prompt.ask("短信验证码（4-6 位）", password=True).strip()
        if len(vcode) < 4:
            console.print("[red]验证码不能为空[/]")
            return

        import time

        console.print(
            "[dim]收到短信后再输入验证码；输入完成后约 5 秒提交登录（避免与发码挤在同一秒）。[/]"
        )
        time.sleep(5)

        with console.status("[green]登录 i茅台…[/]"):
            try:
                token, user_id = client.login(mobile, vcode)
            except RateLimitError as e:
                console.print(
                    Panel(
                        f"[red]{e}[/]\n\n[yellow]处理建议：[/]\n"
                        "1. 等待 2–5 分钟再试\n"
                        "2. 不要连续多次点「发送验证码」\n"
                        "3. 确认验证码正确且未过期\n"
                        "4. 可关闭代理/VPN，换 4G 热点",
                        title="请求过于频繁 (429)",
                        border_style="red",
                    )
                )
                return
            except AuthError as e:
                console.print(f"[red]登录失败: {e}[/]")
                return
            except Exception as e:
                console.print(f"[red]登录异常: {e}[/]")
                return
        console.print("[green]✓ i茅台 登录成功[/]")

    province, city, district, detail, lat, lng, receiver_name, receiver_mobile = (
        _pick_address(
            cfg,
            default_name=old.receiver_name if old else "",
            default_mobile=old.receiver_mobile if old else mobile,
        )
    )

    console.print("\n[bold cyan]━━━ 支付密码（可选）━━━[/]")
    pay_pwd = old.pay_password if old else ""
    if Confirm.ask("保存支付密码到本机?（中签后在 App 支付时可参考）", default=bool(pay_pwd)):
        pay_pwd = Prompt.ask("支付密码（通常 6 位）", password=True, default="")

    end = Prompt.ask("使用截止 YYYYMMDD", default=old.end_date if old else "99991231")

    account = AccountCredentials(
        mobile=mobile,
        token=token,
        user_id=user_id,
        province=province,
        city=city,
        lat=lat,
        lng=lng,
        device_id=device_id,
        end_date=end,
        receiver_name=receiver_name,
        receiver_mobile=receiver_mobile or mobile,
        district=district,
        detail_address=detail,
        pay_password=pay_pwd,
    )

    accounts = [a for a in existing if a.mobile != mobile]
    accounts.append(account)
    save_credentials(accounts, cfg.secret_key)

    t = Table(title="已保存", box=None, show_header=False)
    t.add_column(style="cyan", width=12)
    t.add_column()
    t.add_row("软件", "茅台抢单软件")
    t.add_row("i茅台账号", mask_mobile(mobile))
    t.add_row("收货人", receiver_name)
    t.add_row("电话", receiver_mobile or mobile)
    t.add_row("地址", f"{province}{city}{district}")
    t.add_row("详细", detail)
    console.print(Panel(t, border_style="green"))
    console.print("[bold green]已加密保存[/]")
