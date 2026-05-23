#!/usr/bin/env python3
"""
为 data/credentials.json 批量分配 egress_group（出口分组），便于 IP 隔离。

示例：1000 个号，每 20 个号一组 → 50 个出口，每组对应 proxy_pools 里一个代理。

用法:
  python scripts/assign_egress_groups.py --per-group 20
  python scripts/assign_egress_groups.py --per-group 20 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config_loader import load_config, load_credentials, save_credentials


def main() -> None:
    p = argparse.ArgumentParser(description="批量分配 egress_group")
    p.add_argument(
        "--per-group",
        type=int,
        default=20,
        help="每组账号数量（默认 20，1000 号约需 50 组/50 个 IP）",
    )
    p.add_argument("--prefix", default="ip", help="分组名前缀，如 ip01 ip02")
    p.add_argument("--dry-run", action="store_true", help="只打印不保存")
    args = p.parse_args()

    if args.per_group < 1:
        print("per-group 至少为 1")
        sys.exit(1)

    cfg = load_config()
    accounts = load_credentials(cfg.secret_key)
    if not accounts:
        print("无账号")
        sys.exit(1)

    for i, acc in enumerate(accounts):
        group_idx = i // args.per_group + 1
        acc.egress_group = f"{args.prefix}{group_idx:03d}"

    groups = sorted({a.egress_group for a in accounts})
    print(f"账号数: {len(accounts)}")
    print(f"每组: {args.per_group} → 共 {len(groups)} 个出口组")
    print(f"示例组名: {groups[0]} … {groups[-1]}")
    print()
    print("请在 config.yaml 的 proxy_pools 中为每组配置代理，例如:")
    print("proxy_pools:")
    for g in groups[:3]:
        print(f'  {g}: "http://user:pass@host-for-{g}:port"')
    if len(groups) > 3:
        print(f"  # … 共 {len(groups)} 项")

    if args.dry_run:
        print("\n(dry-run 未写入文件)")
        return

    save_credentials(accounts, cfg.secret_key)
    print(f"\n已写入 {ROOT / 'data' / 'credentials.json'}")


if __name__ == "__main__":
    main()
