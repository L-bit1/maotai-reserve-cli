# i茅台 APK 逆向报告（base.apk.1.1.1）

> 分析对象：`base.apk.1.1.1`（约 61MB）  
> 工具：JADX 1.5.5、androguard、strings、静态解包  
> 结论：**壳加固 + DEX 虚拟机保护**，业务代码不在明文 DEX 中；签名密钥在 **native** 层运行时生成。

---

## 1. 应用身份

| 字段 | 值 |
|------|-----|
| 包名 | `com.moutai.mall` |
| 版本名 | **1.9.6** |
| 版本号 | **196** |
| 启动 Activity | `com.moutai.mall.module.splash.SplashActivity` |
| 真实 Application | `com.moutai.mall.MTApp`（运行时由壳加载） |

---

## 2. 加固结构（为何 JADX 只能看到 300+ 个类）

APK 使用 **梆梆 / Secneo 壳**（`com.secneo.apkwrapper`）：

```
AndroidManifest
    └── com.secneo.apkwrapper.AW          # 壳 Application
            └── 加载 libDexHelper.so      # 解密/加载真实 DEX
                    └── com.moutai.mall.MTApp   # 真实业务入口
```

壳核心类（已反编译）：

- `com.secneo.apkwrapper.H`：`PKGNAME = "com.moutai.mall"`，`b = "com.moutai.mall.MTApp"`
- `com.secneo.apkwrapper.AW`：代理真实 Application，`hn()` / `pn()` 为 native
- `classes.dex`（22MB）：主要为 **AndroidX / 风控 SDK / 壳代码**，**不含** `moutai519`、`actParam`、`/xhr/` 等业务字符串

额外保护：

| 组件 | 作用 |
|------|------|
| `libdexvmp.so` | DEX 虚拟机保护 |
| `libDexHelper.so` / `libdexjni.so` | 运行时解密并加载业务 DEX |
| `libbangcle_risk.so` | 梆梆风控 |
| `libhaotiansec.so` | 茅台系安全（字符串极少，逻辑在 native） |

**结论**：静态反编译 **无法** 直接得到 `MTApp`、网络层、预约逻辑的 Java 源码，必须 **动态脱壳** 或 **抓包**。

---

## 3. 签名与加密（与本 CLI 的关系）

### 3.1 请求 MD5 签名（`src/crypto.py`）

开源社区（如 [iMaoTai-reserve](https://github.com/397179459/iMaoTai-reserve)）与当前项目一致：

```text
md5 = MD5(SALT + 按 key 排序拼接的参数字符串 + timestamp_ms)
SALT = 2af72f100c356273d46284f6fd1dfc08
```

APK 内 **无明文 SALT**，但 1.9.6 仍可能沿用（需抓包或 Frida 校验）。

### 3.2 actParam AES（预约 body）

```text
AES_KEY = qbhajinldepmucsonaaaccgypwuvcjaa
AES_IV  = 2018534749963515
模式    = AES-CBC + PKCS7
```

同样 **未出现在** 静态 DEX 字符串中，与社区脚本一致。

### 3.3 网易易盾签名密钥（重要发现）

`lib/arm64-v8a/libyxsec.so` 导出 JNI：

```text
Java_com_netease_security_key_KeyUtil_getOriginSigKey
```

说明 App 内嵌 **网易安全 KeyUtil**，**原始签名密钥在 native 中计算**，运行时通过 `getOriginSigKey()` 返回。  
若服务端升级校验逻辑，仅改 Python 里的 SALT 可能不够，还需对齐 **KeyUtil** 输出或完整请求头链。

### 3.4 环境检测（libenc.so）

```text
Java_com_netease_yanxuan_envcheck_NEncUtils_exe
Java_com_netease_yanxuan_envcheck_NEncUtils_gct
...
```

用于模拟器/root/调试检测，与 **429 / 登录失败** 可能相关。

---

## 4. 资源配置（assets）

| 路径 | 说明 |
|------|------|
| `assets/rescache/*/mtappconfig.json` | 配置为 **Base64 密文块**（key/common/android/ios），需 App 内解密 |
| `assets/rescache/*/mtshops.json` 等 | 门店/地址等缓存 JSON |
| `assets/defaultv0` | 40KB Base64 文本，疑为加密配置或 DEX 片段 |
| `moutaiapp://reservationentrance` | 深链，预约入口 |

**静态无法解密** `mtappconfig.json`，需在真机 Hook 解密函数或抓包看下发配置。

---

## 5. 与本项目 `src/api.py` 的接口对应

域名（来自开源 + 本项目，非 APK 明文）：

| 域名 | 用途 |
|------|------|
| `app.moutai519.com.cn` | 登录、验证码、预约提交 |
| `static.moutai519.com.cn` | session、门店列表、资源 |
| `h5.moutai519.com.cn` | H5 / 小游戏耐力等 |

典型路径（社区已验证，1.9.6 建议抓包再确认）：

- `POST /xhr/front/user/register/vcode` — 发短信
- `POST /xhr/front/user/register/login` — 登录
- `GET  /mt-backend/xhr/front/mall/index/session/get/{day_ms}`
- `POST /xhr/front/mall/reservation/add` — 预约（含 `actParam`）

---

## 6. 推荐逆向路线（按投入从低到高）

> **没有安卓真机？** 见 [无安卓真机指南.md](./无安卓真机指南.md)（Mac 模拟器 / iPhone 抓包 / 仅用开源参数）。

### 路线 A：HTTPS 抓包（**首选，维护 CLI**）

1. Android **真机或 Mac 模拟器** 安装 **1.9.6**（与 APK 一致或商店最新）
2. mitmproxy / Charles 装证书，抓：发码 → 登录 → 预约
3. 对比 `md5`、`timestamp`、`MT-*` 头、`actParam` 与 `src/crypto.py` 是否一致
4. 不一致则只改 `crypto.py` / `api.py` 中对应常量

### 路线 B：Frida 动态 Hook（**拿 SALT / SigKey**）

项目已提供：`reverse/frida/hook_sig_key.js`

```bash
frida -U -f com.moutai.mall -l reverse/frida/hook_sig_key.js --no-pause
```

在 App 内执行登录/预约，观察控制台是否输出 `getOriginSigKey` 及 Java 层 MD5 入参。

### 路线 C：脱壳后再 JADX（工作量大）

1. 真机运行 App，Frida  dump 内存中解密后的 `classes.dex`
2. 用 JADX 打开 dump 出的 DEX，搜索 `moutai519`、`reservation`、`actParam`
3. 定位签名类与 `KeyUtil` 调用链

---

## 7. 静态分析文件位置

| 路径 | 内容 |
|------|------|
| `reverse/jadx_out/` | JADX 反编译结果（仅壳 + SDK） |
| `reverse/apk_unzip/` | 解包原始文件（已 gitignore，体积大） |
| `reverse/frida/` | Frida 脚本与说明 |
| `docs/APK分析说明.md` | 简要维护说明 |

---

## 8. 给维护者的结论

1. **确认是 i茅台 1.9.6 官方包**，但 **不能** 靠静态 APK 自动更新全部密钥。  
2. **SALT / AES** 与主流开源脚本一致，1.9.6 **大概率仍可用**，必须以抓包验证。  
3. 签名链含 **`KeyUtil.getOriginSigKey`（native）**，深度对抗时需 Frida。  
4. 你遇到的 **HTTP 429** 更可能是 **频控 / 空验证码 / 环境风控**，而非单纯 SALT 过期；先保证验证码非空、降低发码频率，再抓包对比成功请求。

---

*报告生成：JADX + androguard + 原生库 JNI 字符串分析。*
