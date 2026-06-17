# HttpCanary / Reqable 抓包指南（i茅台 1.9.7）

> 适用：无 root 真机。i茅台对 `*.moutai519.com.cn` 有 **SSL Pinning**，mitmproxy 无法解密；**Reqable**（HttpCanary 官方继任）VPN 模式成功率更高。

> **本机已通过 ADB 安装：** `Reqable v3.1.3`（`com.reqable.android`），APK 位于 `reverse/tmp/reqable-app-android-arm64.apk`。

---

## 1. 准备工作（Mac 端已处理）

- 已关闭 mitmproxy，并清除 ADB 全局代理（避免冲突）
- 分析脚本：`reverse/scripts/analyze_har.py`（Reqable 导出 HAR 同样适用）

---

## 2. 手机打开 Reqable（已安装）

1. 桌面找到 **Reqable** 图标并打开（Mac 端已尝试自动启动）
2. 首次打开按提示授予：
   - **VPN 连接**（必须）
   - **悬浮窗**（可选）

若未看到图标：设置 → 应用 → Reqable → 允许安装未知应用后重试。

---

## 3. 配置（避免「设备异常」）

1. Reqable → 开启 **VPN 模式** + **增强模式**
2. **应用程序** → 选 **全部**，**不要**只勾 i茅台（单独钩 i茅台 会弹「设备异常」）
3. 一键推送安全配置：`bash reverse/scripts/adb_reqable_safe_capture.sh`
4. **HTTPS 解密** → 开启 → 按提示安装 **Reqable 根证书**
   - 设置 → 安全 → 加密与凭据 → **从存储设备安装** → CA 证书

---

## 4. 开始抓包

1. Reqable 首页 → 点击 **开始抓包**
2. 打开 **i茅台**，依次操作：
   - 发验证码（或跳过若已登录）
   - **登录**
   - 进入 **申购/预约** 页
   - **提交一次预约**（能点到即可，不必中签）
3. 回到 Reqable → **停止抓包**

---

## 5. 导出 HAR

1. Reqable → **历史/记录** → 选中本次会话
2. **导出** → 格式选 **HAR**
3. 传到 Mac，例如放到：
   ```
   reverse/tmp/imaotai.har
   ```

---

## 6. Mac 上分析

```bash
cd "/Users/mac/Desktop/工作 /软件/茅台抢单软件"
python3 reverse/scripts/analyze_har.py reverse/tmp/imaotai.har
```

报告默认写入 `reverse/tmp/har_analysis.txt`，包含：

- `MT-*` Header（MT-R、MT-V、MT-APP-Version 等）
- 登录/预约 Body（md5、timestamp、actParam）
- 服务端响应 code / message

---

## 7. 若仍抓不到 moutai519

| 现象 | 处理 |
|------|------|
| 弹「设备异常」 | 取消「仅 i茅台」白名单，改用全量 VPN（见上文） |
| 列表里没有 moutai519 | 搜索框输入 `moutai519`；重启抓包后再操作 i茅台 |
| HTTPS 无法解密 | 重装 Reqable 证书；Android 13+ 确认 CA 已启用 |
| 仍失败 | 截图 Reqable 请求列表发开发者 |

---

## 8. 与现有代码对照

抓包完成后重点核对 `src/crypto.py`：

| 字段 | 当前实现 |
|------|----------|
| SALT | `2af72f100c356273d46284f6fd1dfc08` |
| AES KEY/IV | `qbhajinldepmucsonaaaccgypwuvcjaa` / `2018534749963515` |
| MT-APP-Version | 动态 1.9.7 |
| MT-V | 待 HAR 确认是否存在 |

---

## 9. 传回方式

导出 HAR 后：

1. 将文件放到 `reverse/tmp/imaotai.har`，或
2. 在对话中回复 **「HAR 已导出」** 并说明文件路径

我会自动跑 `analyze_har.py` 并更新逆向结论。
