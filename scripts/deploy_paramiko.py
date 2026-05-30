#!/usr/bin/env python3
"""通过 Paramiko 部署到远程 Ubuntu（密码从环境变量 DEPLOY_PASS 读取）。"""

from __future__ import annotations

import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOTE_DIR = "/opt/maotai"
HEX_DIR = re.compile(r"^[0-9a-f]{32}$")


def _make_tarball() -> Path:
    out = Path(tempfile.gettempdir()) / "maotai-deploy.tar.gz"
    excludes = [
        ".venv",
        "node_modules",
        ".git",
        "reverse",
        "备份-合并前-20260519",
        "龙蒙超版本",
        "__pycache__",
        "base.apk*",
        "*.apk",
        ".DS_Store",
        "data/credentials.json",
        "config.yaml",
        ".env",
    ]
    cmd = ["tar", "-czf", str(out), "-C", str(ROOT)]
    for name in excludes:
        cmd.append(f"--exclude={name}")
    # 排除根目录下 32 位十六进制临时目录
    for item in ROOT.iterdir():
        if item.is_dir() and HEX_DIR.match(item.name):
            cmd.append(f"--exclude={item.name}")
    cmd.append(".")
    subprocess.run(cmd, check=True)
    return out


def main() -> int:
    try:
        import paramiko
    except ImportError:
        print("请先: .venv/bin/pip install paramiko", file=sys.stderr)
        return 1

    host = os.environ.get("DEPLOY_HOST", "")
    user = os.environ.get("DEPLOY_USER", "ubuntu")
    password = os.environ.get("DEPLOY_PASS", "")
    if not host or not password:
        print("请设置 DEPLOY_HOST 与 DEPLOY_PASS", file=sys.stderr)
        return 1

    admin_pass = os.environ.get("MT_ADMIN_PASSWORD") or f"Maotai@{secrets.token_hex(4)}"
    secret_key = os.environ.get("MT_SECRET_KEY") or secrets.token_urlsafe(32)
    preserve_env = os.environ.get("DEPLOY_PRESERVE_ENV", "1") != "0"

    print("==> 打包项目（已排除 APK / .venv / node_modules）")
    tar_path = _make_tarball()
    print(f"    包大小 {tar_path.stat().st_size / 1024 / 1024:.1f} MB")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"==> 连接 {user}@{host}")
    client.connect(host, username=user, password=password, timeout=60)
    sftp = client.open_sftp()

    def run_cmd(cmd: str, *, sudo: bool = False, timeout: int = 900) -> str:
        full = cmd if not sudo else f"sudo -S {cmd}"
        _stdin, stdout, stderr = client.exec_command(full, get_pty=True, timeout=timeout)
        if sudo:
            _stdin.write(password + "\n")
        _stdin.channel.shutdown_write()
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        if code != 0:
            raise RuntimeError(f"失败({code}):\n{err}\n{out[-4000:]}")
        return out

    def run_script(script_path: str, *, sudo: bool = False, timeout: int = 900) -> str:
        return run_cmd(f"bash {script_path}", sudo=sudo, timeout=timeout)

    remote_tar = "/tmp/maotai-deploy.tar.gz"
    remote_setup = "/tmp/maotai-setup.sh"
    print("==> 上传")
    sftp.put(str(tar_path), remote_tar)

    setup = f"""#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx curl

BACKUP=/tmp/maotai-data-backup
rm -rf "$BACKUP"
mkdir -p "$BACKUP"
if [ -d {REMOTE_DIR}/data ]; then
  cp -a {REMOTE_DIR}/data "$BACKUP/"
fi
if [ -f {REMOTE_DIR}/deploy/.env ]; then
  cp -a {REMOTE_DIR}/deploy/.env "$BACKUP/.env"
fi
if [ -f {REMOTE_DIR}/config.yaml ]; then
  cp -a {REMOTE_DIR}/config.yaml "$BACKUP/config.yaml"
fi

rm -rf {REMOTE_DIR}
mkdir -p {REMOTE_DIR}
tar -xzf {remote_tar} -C {REMOTE_DIR}
rm -f {remote_tar}
chown -R {user}:{user} {REMOTE_DIR}

mkdir -p {REMOTE_DIR}/data {REMOTE_DIR}/deploy
if [ -d "$BACKUP/data" ]; then
  cp -a "$BACKUP/data/." {REMOTE_DIR}/data/
fi
if [ -f "$BACKUP/config.yaml" ]; then
  cp -a "$BACKUP/config.yaml" {REMOTE_DIR}/config.yaml
fi
if [ -f "$BACKUP/.env" ]; then
  cp -a "$BACKUP/.env" {REMOTE_DIR}/deploy/.env
fi
rm -rf "$BACKUP"

cd {REMOTE_DIR}
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip -q
pip install -r requirements.txt -r backend/requirements.txt -q
test -f config.yaml || cp config.example.yaml config.yaml
test -f deploy/.env || touch deploy/.env

cd web
if ! command -v npm >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi
npm install --silent
npm run build

cp {REMOTE_DIR}/deploy/maotai-api.service /etc/systemd/system/
sed -i 's|User=www-data|User={user}|;s|Group=www-data|Group={user}|' /etc/systemd/system/maotai-api.service
systemctl daemon-reload
systemctl enable maotai-api
systemctl restart maotai-api

cp {REMOTE_DIR}/deploy/nginx-ip.conf /etc/nginx/sites-available/maotai
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/maotai /etc/nginx/sites-enabled/maotai
nginx -t
systemctl reload nginx
echo OK
"""
    local_setup = Path(tempfile.gettempdir()) / "maotai-setup.sh"
    local_setup.write_text(setup, encoding="utf-8")

    sftp.put(str(local_setup), remote_setup)
    sftp.chmod(remote_setup, 0o755)
    local_setup.unlink(missing_ok=True)

    print("==> 安装（约 5～15 分钟，含 npm build）")
    run_script(remote_setup, sudo=True, timeout=1200)

    env_content = f"""MT_ADMIN_USERNAME=admin
MT_ADMIN_PASSWORD={admin_pass}
MT_SECRET_KEY={secret_key}
MT_CORS_ORIGINS=http://{host}
MT_APP_ROOT={REMOTE_DIR}
MT_SCHEDULER_ENABLED=true
MT_SCHEDULER_TIMEZONE=Asia/Shanghai
MT_LOTTERY_CHECK_TIME=18:03:00
MT_TOKEN_CHECK_TIME=07:00:00
MT_WEEKEND_RESERVE_ENABLED=true
MT_WEEKEND_RESERVE_TIME=15:05:00
MT_APP_LATEST_VERSION_CODE=2
MT_APP_LATEST_VERSION_NAME=1.1.0
MT_APP_DOWNLOAD_URL=http://{host}/downloads/maotai-reserve.apk
"""
    local_env = Path(tempfile.gettempdir()) / "maotai.env"
    local_env.write_text(env_content, encoding="utf-8")
    if preserve_env:
        # 若服务器已有 .env，保留；否则写入新配置
        check = run_cmd(
            f"test -f {REMOTE_DIR}/deploy/.env && echo HAS_ENV || echo NO_ENV",
            timeout=30,
        )
        if "HAS_ENV" in check:
            print("==> 保留服务器已有 deploy/.env")
        else:
            print("==> 写入 deploy/.env")
            sftp.put(str(local_env), f"{REMOTE_DIR}/deploy/.env")
    else:
        sftp.put(str(local_env), f"{REMOTE_DIR}/deploy/.env")
    local_env.unlink(missing_ok=True)

    run_cmd("systemctl restart maotai-api", sudo=True)
    status = run_cmd(
        "systemctl is-active maotai-api && curl -s http://127.0.0.1:8000/api/v1/ping",
        sudo=False,
    )

    sftp.close()
    client.close()
    tar_path.unlink(missing_ok=True)

    print(status.strip())
    print(f"\n✅ 部署完成: http://{host}/")
    print(f"   管理员: admin / {admin_pass}")
    print("   请尽快修改服务器 SSH 密码与管理员密码")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
