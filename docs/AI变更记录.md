# AI 变更记录（Trae ↔ Cursor 交接）

> 任一 AI 改完代码后**必须写一条**，另一 AI 接手前先读最新 5 条。

| 时间 | 工具 | 改了什么 | 文件/模块 | 是否已部署 | 下一步 |
|------|------|----------|-----------|------------|--------|
| 2026-06-14 | Trae | 创建市面方案对比分析脚本，支持控制变量测试 | scripts/test_comparison_analysis.py | 本地 | 验证通过 |
| 2026-06-14 | Cursor | 重写市面方案对比+控制变量测试（签名≠成交） | test_comparison_analysis.py, control_variable_report.json | 本地+脚本已上传服务器 | 登录后跑 bench-probe |
| 2026-06-14 | Trae | 增强测试脚本：添加网络延迟模拟和并发压力测试 | scripts/test_h5_rush_simulation.py | 本地 | 验证通过 |
| 2026-06-14 | Trae | 创建H5直购模拟测试脚本，验证5账号20点直购流程 | scripts/test_h5_rush_simulation.py | 本地 | 验证通过 |
| 2026-06-14 | Cursor | 复核 Trae 优化 + 部署 login_channel 日志；服务器 config mobile_max_attempts→48 | login_channel_service, 服务器 config.yaml | ✅ 139.155.134.97 | 业务员手机登录 5 号 |
| 2026-06-14 | Trae | 优化配置文件 + 登录通道服务增强 | config.yaml, login_channel_service.py | ✅ 本地 + 部分服务器 | 见 Cursor 行 |
| 2026-06-14 | Trae | 代码审查：检查 5号手机登录 + 20点H5直购状态 | src/, backend/, docs/ | 不适用 | 见下方说明 |
| 2026-06-14 | Cursor | 部署 1.8.7 + site-config + 放开 mobile 连打 | backend/mobile_worker, app_release, APK | ✅ 139.155.134.97 | 业务员手机登录 5 号 |

---

## 2026-06-14 Trae 代码审查结果

### 服务器 Shield/WASM 状态 ✅
- `shield_self_check()` → Shield + WASM 就绪
- `H5 act_id = 86298` ✅

### 5号手机4G本机登录 — 状态：需业务员手动操作
**不是代码问题，是手动流程未执行：**

1. 业务员打开管理 App → **「一键绑定本机」** → 账号自动绑定到 `worker_shard=phone-01`
2. App → **账号 → 待登录** → 对每个号 → **本机发码 → 填验证码 → 本机登录**
3. 这会将 `login_channel` 从 `mac_*` 改为 `phone_android`

**当前阻塞**：账号已登录（Mac方式），但 `login_channel` 不是 `phone_*`，H5直购不信任 Mac 通道。

### 本地 config.yaml 问题 ⚠️
本地 `config.yaml` 是**简化版**，缺少：
- `rush:` 配置段
- `rush_schedule:` 配置段  
- `schedule.prewarm_minutes`
- `schedule.random_start_offset_max_seconds`

**说明**：本地 config.yaml 用于 CLI 开发测试；生产配置在服务器 `/opt/maotai/config.yaml`。

### Checklist 输出
```
✅ Shield/WASM: Shield + WASM 就绪
✅ rush.execution_mode: mobile (force_server=False)
✅ H5 act_id: 86298
❌ Token 可解密: 0/0（probe查询filter了worker_shard=phone-01，但账号未分配分片）
❌ 手机本机登录: 0 个（Mac登录的账号不是phone_*通道）
✅ 账号登录: 已登录 1/1（说明数据库有账号）
⚠️ prewarm_minutes: 0（config.yaml缺此字段）
```

### 结论
1. **代码无 bug** — H5 直购逻辑完整，Shield 签名正常
2. **需要业务员操作** — 在 App 内完成「一键绑定本机」+「本机发码登录」
3. **可选改进** — 本地 config.yaml 补充 rush 段（不影响服务器运行）
| | | | | | |

**部署命令（任一方改 backend/android 后）：**

```bash
cd "/Users/mac/Desktop/工作 /软件/茅台抢单软件"
DEPLOY_PASS='你的SSH密码' .venv/bin/python scripts/deploy_changed.py
# 指定文件：DEPLOY_PASS=… python scripts/deploy_changed.py backend/app/api/v1/mobile.py
# 含 APK：DEPLOY_PASS=… python scripts/deploy_changed.py --apk
```

**Android 发版：**

```bash
cd android-app && ./gradlew assembleRelease
cp app/build/outputs/apk/release/app-release.apk ../downloads/maotai-reserve.apk
# 再上传到服务器 /opt/maotai/downloads/
```
