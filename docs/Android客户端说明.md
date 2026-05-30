# Android 客户端说明

面向 **单甲方、多 i茅台 账号**（如 1000 号）的手机管理 App，连接你们已部署的云服务器 API。

## 工程位置

`android-app/` — Kotlin + Jetpack Compose + Retrofit

## 功能

| 页签 | 功能 |
|------|------|
| 首页 | 账号统计、一键每日预约（全部启用账号） |
| 账号 | 添加手机号、发验证码、短信登录、编辑地址/选店策略 |
| 预约 | 立即预约、试跑、查看任务进度 |
| 中签 | 同步中签、待付款列表、打开官方 i茅台 App |

## 编译安装

1. 安装 [Android Studio](https://developer.android.com/studio)（Ladybug 或更新）
2. 打开目录 `android-app/`
3. 等待 Gradle 同步完成
4. 连接手机或模拟器 → Run `app`

默认服务器：`http://139.155.134.97/api/v1/`（登录页可修改）

管理账号密码与 Web 相同（如 `admin` / 部署时设置的 `MT_ADMIN_PASSWORD`）。

## 与服务器关系

```text
安卓 App  ──JWT──►  你们的 FastAPI（139.155.134.97）
                      ├── 存账号 Token、地址
                      ├── 定时/一键预约任务
                      ├── 代理池 proxy_pools（服务器配置）
                      └── 请求 i茅台官方
```

用户 **不需要** 在手机上配置 SOCKS5；代理在服务器 `config.yaml` 维护。

## 后端新增接口（需部署到服务器）

- `GET /api/v1/mobile/dashboard` — 首页统计
- `POST /api/v1/mobile/quick-reserve` — 一键预约

更新服务器代码后执行：

```bash
sudo systemctl restart maotai-api
```

## 应用内更新（方式 2）

用户已安装的 App 在**打开时**会自动请求：

`GET /api/v1/app/check-update?version_code=当前版本`

若服务器配置的 `versionCode` 更大，则弹窗 **下载 → 安装**。

### 发布新版本（一条命令）

```bash
export DEPLOY_HOST=139.155.134.97
export DEPLOY_USER=ubuntu
export DEPLOY_PASS='你的SSH密码'
export NEW_VERSION_CODE=2        # 必须大于旧版
export NEW_VERSION_NAME=1.0.1
export RELEASE_NOTES='修复登录；优化预约'
./scripts/publish-android-update.sh
```

脚本会：改 `versionCode` → 编译 APK → 上传到服务器 `/opt/maotai/downloads/` → 更新 `deploy/.env` → 重启 API。

### 手动配置（服务器 `deploy/.env`）

```env
MT_APP_LATEST_VERSION_CODE=2
MT_APP_LATEST_VERSION_NAME=1.0.1
MT_APP_DOWNLOAD_URL=http://139.155.134.97/downloads/maotai-reserve.apk
MT_APP_RELEASE_NOTES=更新说明
MT_APP_FORCE_UPDATE=false
```

Nginx 需提供 `/downloads/` 目录（见 `deploy/nginx-ip.conf`）。

### 签名说明

覆盖安装需 **同一签名**。正式环境请固定 release keystore；debug 包换电脑重签可能需先卸载旧版。

## 发布 APK（手动）

Android Studio → Build → Build APK(s)

或使用 `./scripts/publish-android-update.sh`

正式环境建议：绑定域名 + HTTPS，并修改 `DEFAULT_API_BASE`。
