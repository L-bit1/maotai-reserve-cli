# i茅台 APK 分析说明（base.apk.1.1.1）

本文档基于项目目录中的 **`base.apk.1.1.1`**（约 61MB）做静态分析结论，供开发维护 CLI 时参考。

**完整逆向报告**（壳结构、JNI、Frida 路线）：见 [APK逆向报告.md](./APK逆向报告.md)。

---

## 1. 文件识别

| 项目 | 结论 |
|------|------|
| 文件类型 | 标准 Android APK（Zip） |
| 包名（DEX 字符串） | **`com.moutai.mall`** → 确认为 i茅台 官方应用 |
| 版本名 / 版本号 | **1.9.6 / 196**（androguard 解析） |
| 文件名 `1.1.1` | 多为 **Base 模块 / 内部版本号**，与商店版本号可能不一致 |
| 真实 Application | `com.moutai.mall.MTApp`（由 Secneo 壳 `AW` 动态加载） |

---

## 2. 安全防护（为何难以从 APK 直接抠接口）

APK 内含多套安全/加固相关原生库，例如：

| 库名 | 常见用途 |
|------|----------|
| `libhaotiansec.so` | 茅台系安全组件 |
| `libenc.so` | 加密相关 |
| `libdexvmp.so` / `libDexHelper` | DEX 保护 / 虚拟机保护 |
| `libbangcle_risk.so` | 梆梆等风控 |

**静态扫描结果：**

- APK 二进制中 **未发现** 明文 `app.moutai519.com.cn`
- **未发现** 开源脚本里常用的 `SALT` / `AES_KEY` 明文字符串
- 接口路径、`actParam` 算法很可能在 **运行时解密** 或 **服务端下发**

因此：**不能指望** 仅靠解包 APK 就自动更新本项目的 `crypto.py`，仍需 **真机抓包** 或 **Frida 动态分析**（门槛较高）。

---

## 3. 与本 CLI 工具的关系

| 数据来源 | 适用场景 |
|----------|----------|
| **本 APK 静态分析** | 确认包名、了解加固情况；**难以**直接导出最新密钥 |
| **App Store / 商店版本号** | 用于 `MT-APP-Version`（本项目已自动拉 iOS 版本，Android 建议与商店一致） |
| **Charles / mitmproxy 抓包** | **推荐**：登录、发验证码、预约时记录 URL、Header、Body |
| **GitHub 开源 imaotai 项目** | 社区更新 SALT/AES 时的参考 |

---

## 4. 推荐使用方式（结合 APK）

1. 在 **Android 手机** 安装与 APK 同源的 i茅台（或官方商店最新版）。  
2. 手机安装抓包证书，抓取一次完整流程：  
   - 发送验证码  
   - 登录  
   - 预约提交  
3. 对比抓包结果与 `src/api.py`、`src/crypto.py`，按需更新。  
4. **勿将 APK 提交到 Git**（体积大、版权与合规风险）；已加入 `.gitignore`。

---

## 5. 深度逆向（本仓库已提供）

| 工具 / 路径 | 说明 |
|-------------|------|
| **JADX**（本机 `brew install jadx`） | 反编译结果在 `reverse/jadx_out/`（仅壳层，约 328 个 Java 文件） |
| **Frida** | `reverse/frida/hook_sig_key.js`、`hook_md5.js` — Hook `KeyUtil.getOriginSigKey` 与 MD5 |
| **JNI 列表** | `bash reverse/scripts/list_jni.sh` |

关键 native：`libyxsec.so` → `Java_com_netease_security_key_KeyUtil_getOriginSigKey`

个人学习请遵守法律法规与用户协议。

---

## 6. 结论（给乙方维护用）

- `base.apk.1.1.1` **是 i茅台 安装包**，可用于确认目标 App。  
- **不能** 替代抓包来维护预约脚本；当前 CLI 的接口参数仍以 **抓包 + 开源社区** 为主。  
- 文件名版本 **1.1.1** 与商店 **1.9.x** 可能不一致，抓包时请以 **实际安装版本** 为准。

---

*分析环境：macOS，JADX 1.5.5 + androguard + 原生库 JNI 检索；业务 DEX 需动态脱壳或抓包。*
