#!/usr/bin/env python3
"""首次配置：登录 i茅台 并保存账号信息。"""

import logging
import sys
from datetime import datetime

from src.api import IMaotaiClient, new_device_id
from src.config_loader import (
    AccountCredentials,
    load_config,
    load_credentials,
    save_credentials,
    validate_secret_key,
)
from src.geocode import geocode_address

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)


def pick_location(amap_key: str) -> tuple[str, str, str, str]:
    while True:
        addr = input("请输入小区/地标名称（用于匹配附近门店）: ").strip()
        if not addr:
            continue
        geocodes = geocode_address(amap_key, addr)
        if not geocodes:
            print("未找到地址，请重试")
            continue
        for i, g in enumerate(geocodes):
            print(f"  [{i}] {g.get('province')}{g.get('city')} {g.get('formatted_address')}")
        choice = input("选择序号 [0]: ").strip() or "0"
        if not choice.isdigit() or int(choice) >= len(geocodes):
            print("无效序号")
            continue
        g = geocodes[int(choice)]
        lng, lat = g["location"].split(",")
        return str(g["province"]), str(g["city"]), lat, lng


def main() -> None:
    cfg = load_config()
    try:
        validate_secret_key(cfg.secret_key)
    except Exception as e:
        print(e)
        sys.exit(1)
    if not cfg.amap_key:
        print("请先在 config.yaml 中设置 amap_key（高德地图 Key）")
        sys.exit(1)

    mobile = input("手机号: ").strip()
    if len(mobile) != 11 or not mobile.isdigit():
        print("手机号格式不正确")
        sys.exit(1)

    province, city, lat, lng = pick_location(cfg.amap_key)
    print(f"已选: {province} {city} ({lat}, {lng})")

    device_id = new_device_id()
    placeholder = AccountCredentials(
        mobile=mobile,
        token="",
        user_id="0",
        province=province,
        city=city,
        lat=lat,
        lng=lng,
        device_id=device_id,
    )
    client = IMaotaiClient(placeholder, proxy_pools=cfg.proxy_pools)

    ok, msg = client.send_vcode(mobile)
    if not ok:
        print(msg)
        sys.exit(1)
    print(msg)
    code = input("短信验证码（4-6位）: ").strip()
    if len(code) < 4:
        print("验证码不能为空")
        sys.exit(1)
    import time
    time.sleep(2)
    token, user_id = client.login(mobile, code)
    print(f"登录成功 userId={user_id}")

    end = input("账号有效期 YYYYMMDD [99991231]: ").strip() or "99991231"

    accounts = load_credentials(cfg.secret_key)
    accounts = [a for a in accounts if a.mobile != mobile]
    accounts.append(
        AccountCredentials(
            mobile=mobile,
            token=token,
            user_id=user_id,
            province=province,
            city=city,
            lat=lat,
            lng=lng,
            device_id=device_id,
            end_date=end,
        )
    )
    save_credentials(accounts, cfg.secret_key)
    print(f"已加密保存到 data/credentials.json，共 {len(accounts)} 个账号")
    print(f"完成时间: {datetime.now():%Y-%m-%d %H:%M:%S}")


if __name__ == "__main__":
    main()
