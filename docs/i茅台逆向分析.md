# i茅台 App 逆向分析（技术参考）

> 本文基于本仓库 `src/api.py`、`src/crypto.py`、`src/device_util.py` 及社区开源项目（[ken-iMoutai-Script](https://github.com/AkenClub/ken-iMoutai-Script)、[campus-imaotai](https://github.com/oddfar/campus-imaotai)、[insoxin/imaotai](https://github.com/insoxin/imaotai)）整理，供后续 Frida/抓包逆向时对照。**仅用于学习与自有账号自动化管理。**

---

## 1. 总体架构

```text
┌─────────────┐     HTTPS JSON      ┌──────────────────────────────┐
│  i茅台 App  │ ◄──────────────────►│ app.moutai519.com.cn         │
│  (iOS)      │                     │ static.moutai519.com.cn      │
└─────────────┘                     │ h5.moutai519.com.cn          │
       │                            └──────────────────────────────┘
       │ MT-Token / MT-R / actParam              ▲
       ▼                                         │
┌─────────────┐         同协议模拟               │
│ 本仓库 CLI  │ ─────────────────────────────────┘
│ Web/API     │
└─────────────┘
```

App 与脚本本质相同：**REST + 自定义签名 + AES 业务体**，风控看 **IP、设备指纹、频率、App 版本**。

---

## 2. 域名与职责

| 域名 | 用途 |
|------|------|
| `app.moutai519.com.cn` | 登录、用户信息、**预约提交** `/xhr/front/mall/reservation/add` |
| `static.moutai519.com.cn` | 场次 sessionId、门店 JSON、商品库存 slim 列表 |
| `h5.moutai519.com.cn` | 小茅运/旅行/耐力 H5 小游戏、周末专场部分接口 |

---

## 3. 认证与设备指纹

### 3.1 登录链路（发码 → 登录）

| 步骤 | 路径 | 要点 |
|------|------|------|
| 发码 | `POST /xhr/front/user/register/vcode` | Body 含 `mobile` + **签名**；`MT-Token` 必须为空 |
| 登录 | `POST /xhr/front/user/register/login` | `mobile`, `vCode`, `ydToken`, `ydLogId` |

**请求签名（本仓库 `src/crypto.py`）：**

```text
md5 = MD5( SALT + sorted(params values concatenated) + timestamp_ms )
SALT = "2af72f100c356273d46284f6fd1dfc08"
Body 额外字段: md5, timestamp, MT-APP-Version
```

与 [insoxin/imaotai](https://github.com/insoxin/imaotai) 文档一致（早期称 Client_Secret / MD5 链）。

### 3.2 关键 Header

| Header | 含义 | 生成方式（本仓库） |
|--------|------|-------------------|
| `MT-Device-ID` | UUID 大写 | 登录时生成并持久化 |
| `MT-R` | 设备校验串 | `clips_` + Base64(XOR 变换 device_id)，见 `make_mt_r()` |
| `MT-Info` | 设备信息 MD5 | 稳定指纹或随机 |
| `MT-APP-Version` | App 版本 | App Store lookup `id=1600482450`，失败兜底 `1.9.6` |
| `MT-Token` | 登录 JWT/会话 | 登录返回 `data.token` |
| `MT-Network-Type` | WIFI/4G/5G | 反检测配置 |
| `User-Agent` | iOS 设备 UA | 如 `iOS;17.0;Apple;iPhone15,2` |
| `MT-Request-ID` | 请求 UUID | 每次请求刷新 |
| `MT-Lat` / `MT-Lng` | 地理 | 账号/profile 配置 |

**逆向重点：** 新版 App 可能增加 **MT-V**、Shield 等（见 [irabbit666666/imoutai](https://github.com/irabbit666666/imoutai) 商业算法）。当前预约主链路仍以上表 + `actParam` 为主。

### 3.3 MT-R 算法（已还原）

```python
# device_util.make_mt_r — XOR 逐字符后 Base64，前缀 clips_
xor_val = 72
for ch in device_id:
    xor_val ^= ord(ch)
    append chr(xor_val)
```

[insoxin](https://github.com/insoxin/imaotai) 博客称 MD5(`2af72f100c356273d46284f6fd1dfc08` + 排序数据 + 时间戳)，与登录签名 SALT 同源。

---

## 4. 预约（申购）链路

### 4.1 时序

```text
1. GET session/get/{day_ms}     → sessionId（9 点前常为 0，需轮询）
2. GET mall/resource/get        → 全国门店 JSON URL
3. GET shop/list/slim/v3/...    → 当日各店库存
4. POST reservation/add         → 提交申购
5. GET reservation/list/...     → 复核 / 中签查询
```

### 4.2 actParam 加密

```python
# AES-128-CBC, PKCS7
KEY = "qbhajinldepmucsonaaaccgypwuvcjaa"
IV  = "2018534749963515"
明文 JSON: { itemInfoList, sessionId, userId, shopId }
外层 POST body: { itemInfoList, sessionId, shopId, actParam }  # userId 有时省略
```

**逆向入口：** App 内 `ActParam` / `encrypt` 相关 native 或 JSBridge；版本升级后 KEY/IV 可能轮换（需 re-hook）。

### 4.3 常见业务码

| code | 含义 | 处理 |
|------|------|------|
| 2000 | 成功 | — |
| 4820 | 版本过低 | 更新 `MT-APP-Version`（ken FAQ） |
| 401/4030 | Token 失效 | 重新登录 |
| 429 | 频率/风控 | 换 IP、降并发 |

本仓库：`src/imaotai_errors.py` + 预约后 `verify_item_reserved_today()` 复核。

---

## 5. H5 / 养号子系统

| 功能 | 域名 | 认证 |
|------|------|------|
| 领取耐力 | `/game/isolationPage/getUserEnergyAward` | Cookie `MT-Token-Wap` |
| 小茅运旅行 | `/game/xmTravel/*` | 同上 |
| 周末欢乐购 | `/xhr/front/mall/index/special/session/getByType/3` | 静态头 + Token |
| 小茅好运专场 | `/xhr/front/mall/index/special/session/get` | 静态头 + Token；预约 itemList **全部**商品 |

参考：[mrabit/xmtravel](https://github.com/mrabit/xmtravel)、ken `5_travel.py`。

---

## 6. 风控面（EdgeOne / 行为）

| 维度 | 现象 | 本仓库对策 |
|------|------|------------|
| 出口 IP | 机房 IP 发码/预约 429 | `proxy_pools` + `egress_group` |
| 频率 | 同 IP 短时多号 | `login_vcode_interval`, `max_reserve_per_minute` |
| 指纹 | 多号同 UA/设备 | `stable_fingerprint` 每号独立 |
| 行为 | 9 点瞬时并发 | 预热、`account_stagger`、捡漏波次 |
| 版本 | 4820 | `fetch_app_version()` 自动拉取 |

**无手机 100 号：** 必须 **多住宅/4G 出口**，不能靠单服务器 IP（见 `docs/无手机大规模部署方案.md`）。

---

## 7. 与开源项目对比（采纳项）

| 来源 | 优于本仓库之处 | 已采纳 |
|------|----------------|--------|
| [ken-iMoutai-Script](https://github.com/AkenClub/ken-iMoutai-Script) | 指定店换店；4820；98 复核；**小茅好运专场**；`KEN_IMAOTAI_ENV` | ✅ `shop_selector` / `verify_item_reserved_today` / `fetch_lucky_special_session` / `scripts/export_ken_env.py` |
| [campus-imaotai](https://github.com/oddfar/campus-imaotai) | Java 管理端；**定时随机偏移** | ✅ Web 已覆盖；`schedule.random_start_offset_max_seconds` |
| [mrabit/xmtravel](https://github.com/mrabit/xmtravel) | 旅行+分享；**Bark 推送** | ✅ `run_travel` + `shareReward`；`bark_url` + `push_notify` |
| [397179459/iMaoTai-reserve](https://github.com/397179459/iMaoTai-reserve) | 凭证 AES、GitHub Actions | 本仓库 DB + Token 加密已有（Actions 未采纳） |
| [insoxin/imaotai](https://github.com/insoxin/imaotai) | 早期 Docker 一体化 | 已归档，算法淘汰 |
| H5 Shield / actParam 售卖 | 新版抢购 | 本仓库 `src/shield` + `h5_rush.py` 部分覆盖 |

详见 `docs/开源方案学习与采纳.md`。

---

## 8. 建议逆向步骤（下一阶段）

### 8.1 抓包

1. iPhone 安装 i茅台，Charles/mitmproxy + 证书
2. 记录：**发码、登录、sessionId、reservation/add** 全 Header/Body
3. 对比本仓库 `_headers` 与真机差异（尤其 **MT-R、MT-V、MT-Info**）

### 8.2 Frida（iOS）

```text
目标类/函数（随版本变化，需动态搜索）:
- ActParam / encrypt 相关
- MT-R 生成
- 网络层 AFNetworking/NSURLSession 拦截
```

Hook `CCCrypt` / 自定义 native 导出，对照 `src/crypto.py` 明文结构。

### 8.3 Android（若分析 base.apk）

- 解包 `com.moutai.mall`
- 搜索 `actParam`、`reservation/add`、`clips_`
- 对比 `backend` 引用的 `1.9.6` 兜底版本

### 8.4 回归验证

```bash
python check.py          # 健康 + 版本
python main.py --dry-run # 试跑选店加密
# 单号 + 代理发码登录后正式预约
```

---

## 9. 支付 / 代扣（合同第 5 条）

中签后支付在 **App 内收银台** 或银行通道完成，抓包可见 H5/原生支付 URL，但通常含 **一次性支付签名 + 用户生物/密码**，**无法合法做后台批量代扣**。本仓库仅做待付款汇总与标记。

---

## 10. 文件索引（本仓库）

| 文件 | 内容 |
|------|------|
| `src/api.py` | IMaotaiClient 全接口 |
| `src/crypto.py` | 签名 + actParam AES |
| `src/device_util.py` | MT-R、UA、指纹 |
| `src/runner.py` | 预约编排、换店、复核 |
| `src/shop_selector.py` | 选店策略 |
| `src/h5_rush.py` | H5 优先购 |
| `src/imaotai_errors.py` | 业务码说明 |
| `src/risk_control.py` | 429 冷却、节流 |

---

## 12. 动态逆向会话记录（2026-05-27）

### 12.1 环境状态

| 项 | 状态 |
|----|------|
| Mac ADB | `/opt/homebrew/bin/adb` 可用 |
| USB 物理连接 | **WIKO** 已识别（Vendor 0x12d1），序列号 `4ZQ9K25627012467` |
| ADB 设备列表 | **空** — 未开启 USB 调试或未授权本机 |
| Frida | 项目 `.venv-re` 已装 **17.10.1** |
| 静态 APK | `base.apk.1.1.1` v1.9.6，梆梆壳 |
| native 签名 | `libyxsec.so` 导出 `Java_com_netease_security_key_KeyUtil_getOriginSigKey`（已复核） |

### 12.2 手机端必做（解锁 ADB）

1. **开发者选项** → 打开 **USB 调试**
2. USB 模式改为 **文件传输 / MTP**（不要仅充电）
3. 弹窗 **允许 USB 调试** → 勾选始终允许
4. Mac 上执行：`bash reverse/scripts/adb_connect.sh`，应看到 `device` 状态

**无线备选（Android 11+）：** 开发者选项 → 无线调试 → 配对码 →  
`adb pair IP:PORT CODE` → `adb connect IP:5555`

### 12.3 动态抓包命令

```bash
# ADB 就绪后
bash reverse/scripts/run_frida_capture.sh
```

脚本会附加 `com.moutai.mall`，Hook：

- OkHttp：`moutai519` 全 URL 的 **MT-* Header**、请求体、响应体
- `KeyUtil.getOriginSigKey()`：网易 native 签名密钥
- MD5：含 `2af72f` / `mobile` / `vCode` 的输入串
- `Cipher.doFinal`：含 `itemCode`/`shopId` 的 AES 明文（actParam 探测）

**请在 App 内依次操作：** 发验证码 → 登录 → 预约页 → 提交一次。

### 12.4 与现有 Python 实现对照点

抓包时重点核对：

| 字段 | 本仓库 | 待验证 |
|------|--------|--------|
| SALT | `2af72f100c356273d46284f6fd1dfc08` | Frida MD5 输入 |
| AES KEY/IV | `qbhajinldepmucsonaaaccgypwuvcjaa` / `2018534749963515` | Cipher 明文 |
| MT-R | `clips_` + XOR Base64 | 响应 Header |
| MT-APP-Version | 动态 lookup / 1.9.6 | 真机 Header |
| MT-V / Shield | 未实现 | 是否出现在新版 Android |

### 12.6 会话续（用户授权 ADB 后）

| 项 | 结果 |
|----|------|
| 设备 | WIKO **JLG-AN00**（`4ZQ9K25627012467`） |
| 已装 App | `com.moutai.mall` **1.9.7**（versionCode 197） |
| 拉取 APK | `reverse/tmp/base_1.9.7.apk`（64MB，MD5 `c10d6160…`） |
| Frida 附加 | **失败** — `unable to connect to remote frida-server: closed` |
| Root | **无**（`su` 不可用，`run-as` 报 not debuggable） |
| logcat | Release 包几乎不打印 API 明文 |

**Frida 失败原因：** 非 root 真机无法稳定运行/注入 frida-server；梆梆壳对 `com.moutai.mall` 有反调试，即使 `frida-ps` 能列进程也无法 attach。

**1.9.7 vs 1.9.6：** APK 体积 +640KB；壳结构相同（Secneo + libyxsec KeyUtil）；DEX 内仍无明文 `moutai519` 字符串。App Store lookup 已返回 **1.9.7**，本仓库 `fetch_app_version()` 会自动对齐。

**下一步（HTTPS 抓包，无需 root）：**

1. 手机与 Mac 连同一 WiFi  
2. Mac 安装 mitmproxy：`brew install mitmproxy` 或 `.venv-re/bin/pip install mitmproxy`  
3. 手机 WiFi → 代理 → 手动 → Mac 局域网 IP : **8080**  
4. 手机浏览器打开 `http://mitm.it` 安装 Android 证书  
5. 运行 `mitmdump -w reverse/tmp/imaotai.flows` 后在 App 内登录/预约  
6. 若 SSL Pinning 拦截，需 HttpCanary（VPN 模式）或 root + JustTrustMe

### 12.7 本体逆向完成（1.9.7 静态 + 动态）

| 项 | 结论 |
|----|------|
| 完整报告 | [`docs/i茅台1.9.7逆向报告.md`](./i茅台1.9.7逆向报告.md) |
| JADX | 328 类，仅壳 + Everisk；`com.moutai.mall` 仅 `R.java` |
| Manifest | 101 个业务 Activity；壳 `AW` → 运行时 `MTApp` |
| Native | `libyxsec` KeyUtil、`libenc` NEncUtils、`libbangcle_risk` VPN/SSL 检测 **与 1.9.6 同 hash**（除 DexHelper +55KB） |
| mitmproxy | `moutai519` TLS Pinning，无法解密 |
| Reqable | 仅抓 i茅台 → **设备异常**；全量 VPN 可开 App 仍无明文 |
| 方案三 | `protocol_verify.py` **通过** — SALT/AES/Token/门店 1.9.7 可用 |

**维护建议**：CLI 继续用 `MT-APP-Version: 1.9.7`；完整预约链在 **9:00–10:00** `main.py --dry-run` 复核；若要 App 内算法源码需 **root + 脱壳/Frida**。

### 12.8 第 2 轮静态逆向（2026-06-06，非申购窗）

- 真机 **未连 ADB**；用已有 `base_1.9.7.apk` + 公开 API
- `sessionId=0`、可约商品 **0** → 活动未开始，**正常**
- 新域名：`resource.moutai519.com.cn`（配置/门店 zip 下发）
- UI：**Compose**；支付：`mtpaysdk` + 银联 + 支付宝
- `RiskStub.dex` 含 Frida/Xposed/Magisk/SSL 检测字符串
- 离线解包：`mtshops.json` 明文；`mtpopupview` 含 `moutaiapp://reservationentrance`
- 详报：[`reverse/tmp/reverse_session2_2026-06-06.md`](../reverse/tmp/reverse_session2_2026-06-06.md)

---

## 11. 免责声明

接口与算法随茅台 App 更新而失效；自动化可能违反平台用户协议。请在合法合规前提下使用，中签结果由官方抽签决定，软件不保证任何中签率。
