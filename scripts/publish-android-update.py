#!/usr/bin/env python3
"""上传 APK 并更新服务器版本配置。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    host = os.environ["DEPLOY_HOST"]
    user = os.environ.get("DEPLOY_USER", "ubuntu")
    password = os.environ["DEPLOY_PASS"]
    apk_src = os.environ["APK_SRC"]
    version_code = int(os.environ["NEW_VERSION_CODE"])
    version_name = os.environ["NEW_VERSION_NAME"]
    notes = os.environ.get("RELEASE_NOTES", "")
    force = os.environ.get("FORCE_UPDATE", "false").lower() in ("1", "true", "yes")

    remote_dir = "/opt/maotai/downloads"
    env_path = "/opt/maotai/deploy/.env"
    download_url = f"http://{host}/downloads/maotai-reserve.apk"

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"==> 连接 {host}")
    c.connect(host, username=user, password=password, timeout=30)

    def sudo(cmd: str) -> None:
        _i, o, _e = c.exec_command(f"sudo -S bash -lc {cmd!r}", get_pty=True)
        _i.write(password + "\n")
        _i.channel.shutdown_write()
        code = o.channel.recv_exit_status()
        if code != 0:
            raise RuntimeError(o.read().decode(errors="replace"))

    sudo(f"mkdir -p {remote_dir} && chown {user}:{user} {remote_dir}")
    sftp = c.open_sftp()
    print("==> 上传 APK")
    sftp.put(apk_src, f"{remote_dir}/maotai-reserve.apk")

    for rel in [
        "backend/app/api/v1/app_release.py",
        "backend/app/core/config.py",
        "backend/app/api/v1/router.py",
        "deploy/nginx-ip.conf",
    ]:
        local = ROOT / rel
        if local.exists():
            sftp.put(str(local), f"/opt/maotai/{rel}")
            print(f"    更新 {rel}")

    sftp.close()

    def set_env(key: str, value: str) -> None:
        esc = value.replace("'", "'\"'\"'")
        sudo(
            f"touch {env_path} && "
            f"(grep -q '^{key}=' {env_path} && sed -i 's|^{key}=.*|{key}={esc}|' {env_path} || "
            f"echo '{key}={esc}' >> {env_path})"
        )

    set_env("MT_APP_LATEST_VERSION_CODE", str(version_code))
    set_env("MT_APP_LATEST_VERSION_NAME", version_name)
    set_env("MT_APP_DOWNLOAD_URL", download_url)
    set_env("MT_APP_RELEASE_NOTES", notes)
    set_env("MT_APP_FORCE_UPDATE", str(force).lower())

    sudo("systemctl restart maotai-api")
    try:
        sudo(
            "cp /opt/maotai/deploy/nginx-ip.conf /etc/nginx/sites-available/maotai && "
            "nginx -t && systemctl reload nginx"
        )
    except Exception:
        print("（nginx 未更新，请手动添加 /downloads/ 静态目录）")

    c.close()
    print(f"\n✅ 发布完成 versionCode={version_code} ({version_name})")
    print(f"   下载: {download_url}")
    print("   用户打开 App 将提示更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
