# 方案二：Reqable 仅抓 i茅台（已部分自动化）

## Mac/ADB 已替你完成

| 项 | 状态 |
|----|------|
| Reqable 3.1.3 安装 | ✓ |
| CA 证书 | ✓ 用户目录已安装 |
| 增强模式 | ✓ 已开启 |
| **仅抓 i茅台（`whitelistAppIds` / 应用程序只勾 i茅台）** | ❌ **必弹**「设备异常」 |
| **全量 VPN + 增强模式（不勾应用白名单）** | ✓ i茅台 **可进首页**（Pinning 仍挡 moutai519 明文） |
| moutai519 明文 | ✗ **仍无**（Flutter + SSL Pinning，非 Root 无解） |

配置文件路径（手机）：

```text
/storage/emulated/0/Android/data/com.reqable.android/files/user/0/config/capture_builtin
```

本仓库备份：

| 文件 | 用途 |
|------|------|
| `reverse/tmp/capture_builtin_safe.json` | **推荐**：无白名单，不触发设备异常 |
| `reverse/tmp/capture_config_safe.json` | 全量 VPN + 增强模式 |

---

## ⚠️ 避免「设备异常」（必读）

梆梆风控会检测 **仅对 i茅台 做 VPN/代理注入**（Reqable「应用程序」只勾 i茅台，或 `capture_builtin` 里写 `whitelistAppIds: ["com.moutai.mall"]`）。

**正确做法：**

1. 使用 **全量 VPN**，应用程序选 **全部 / (0)**，不要只勾 i茅台
2. 一键推送安全配置：

   ```bash
   bash reverse/scripts/adb_reqable_safe_capture.sh
   ```

3. 抓包后在 Reqable **搜索 `moutai519`** 过滤，再导出 HAR

**错误做法（会弹窗）：**

```json
"whitelistAppIds": ["com.moutai.mall"]
```

---

## 请你手动完成（界面是 Flutter，ADB 点不到列表）

1. 打开 **Reqable** → 右上角 **菜单** → **应用程序**
2. 确认 **未单独勾选 i茅台**（应显示 **`应用程序 (0)`** 或「全部」）
3. 开启 **VPN + 增强模式** → 点 **开始抓包**
4. 再打开 **i茅台** 操作

---

## 抓包操作

1. Reqable 点右下角 **开始抓包**（VPN 图标）
2. 打开 **i茅台** → **登录** → **本月申购 / i购** → **提交预约**
3. Reqable **停止抓包** → **导出 HAR** → 放到 Mac：

   ```text
   reverse/tmp/imaotai.har
   ```

4. Mac 分析：

   ```bash
   python3 reverse/scripts/analyze_har.py reverse/tmp/imaotai.har
   ```

---

## 若 HAR 里仍没有 moutai519

i茅台 1.9.7 使用 **SSL Pinning + 内置 CA Store**（梆梆/网易），非 Root 下 Reqable **无法解密** `*.moutai519.com.cn`。

可选升级（仍属方案二生态）：

| 方式 | 条件 | 说明 |
|------|------|------|
| Reqable **协同模式** | Mac 安装 Reqable 桌面版 | 手机扫电脑二维码，流量在 Mac 查看；**不能单独解决 Pinning** |
| Reqable **Magisk 系统证书模块** | Root + Magisk | 设置 → 证书 → 安装到系统区 |
| **LSPosed + SSLUnpinning** | Root | 对 `com.moutai.mall` 勾选模块后重启 App |
| 回退 **方案三** | 无 Root | 用本仓库 `src/api.py` 脚本直连验证协议 |

### Mac 协同模式（可选）

```bash
# 下载安装 Reqable Mac（arm64）
open https://github.com/reqable/reqable-app/releases/download/3.1.3/reqable-app-macos-arm64.dmg
```

手机 Reqable → **协同模式** → 扫 Mac 二维码 → 再操作 i茅台。

---

## 一键脚本

```bash
# 推荐：全量 VPN，避免设备异常
bash reverse/scripts/adb_reqable_safe_capture.sh
```

---

## 当前结论

- **方案二在无 Root 下最多做到**：VPN 仅路由 i茅台、避免环境弹窗、抓到加密连接元数据。
- **要拿到 actParam / MT-R 明文**：必须 Root + Pinning 绕过，或改用本仓库已有逆向参数（`src/crypto.py`）做脚本验证。
