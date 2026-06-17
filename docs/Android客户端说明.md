# Android 客户端说明（模式 B · 手机 Worker）

面向 **业务员用手机** 完成 i茅台 **发码登录 + 预约**，数据同步到云服务器。  
**i茅台 请求走手机 4G**，不经服务器公网 IP（避免 429）。

## 工程位置

`android-app/` — Kotlin + Jetpack Compose + Retrofit + 本机 i茅台客户端（`imaotai/`）

## 功能

| 页签 | 功能 |
|------|------|
| 首页 | 统计、**等到 9 点本机预约**、立即预约、试跑 |
| 账号 | 添加手机号、**本机发码**、**本机登录**、编辑地址/选店 |
| 预约 | 本机立即预约 / 试跑；查看历史服务器任务 |
| 中签 | 同步中签、待付款、打开官方 i茅台 App |

## 编译安装

1. 安装 [Android Studio](https://developer.android.com/studio)
2. 打开 `android-app/` → Gradle 同步 → Run
3. 当前版本：**1.6.0**（`versionCode=7`：待登录列表、Wi-Fi 检测、9 点前台服务、nearest 选店）

默认服务器：`http://你的服务器/api/v1/`（登录页可改）

## 架构（模式 B）

```text
安卓 App
  ├── 蜂窝网 → i茅台官方（发码/登录/预约）
  └── Wi-Fi/4G → 你们 FastAPI（JWT，存 Token、回写记录）
```

业务员 **不需要** 配置代理；请 **关闭 Wi-Fi，用 4G/5G** 操作发码与预约。

详细 SOP 见 **`docs/手机Worker模式B.md`**。

## 后端接口（需部署）

| 接口 | 说明 |
|------|------|
| `GET /api/v1/mobile/dashboard` | 首页统计 |
| `POST /api/v1/mobile/sync-login/{id}` | 本机登录同步 Token |
| `GET /api/v1/mobile/worker-bundle` | 拉凭证执行预约 |
| `POST /api/v1/mobile/report-reserve` | 回写预约结果 |
| `POST /api/v1/mobile/quick-reserve` | 旧模式：服务器执行（易 429，不推荐） |

```bash
sudo systemctl restart maotai-api
```

## 应用内更新

`GET /api/v1/app/check-update?version_code=当前版本`

发布：

```bash
export NEW_VERSION_CODE=5
export NEW_VERSION_NAME=1.4.0
export RELEASE_NOTES='模式B：本机发码登录与预约'
./scripts/publish-android-update.sh
```

## 与 Mac 本机脚本关系

| 场景 | 工具 |
|------|------|
| 业务员现场 | Android App 模式 B |
| 批量 50+ 号登录 | Mac `batch_local_login.py` |
| 办公室定时抢 | Mac `local_worker.py` + 热点 |

三者共用 `remote-login` / `worker-bundle` 同一套服务器 API。
