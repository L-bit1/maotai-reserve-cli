# 明天 A/B 测试备忘（91HTTP vs 快代理）

> 服务器：`139.155.134.97` · 时区 `Asia/Shanghai`  
> 最后核对：2026-06-11 00:22

---

## 一、测试目标

| 对比项 | ip001（91HTTP 贵阳电信） | kd001（快代理 IDC） |
|--------|--------------------------|---------------------|
| 账号数 | 5 个已登录 | 5 个已登录 |
| 预约 | 10941 享约申购 | 同左 |
| H5 抢购 | `itemPriorityActId=86298` | 同左 |

**账号分组（已锁定）：**

| 池 | 账号 ID | 手机尾号 |
|----|---------|----------|
| **ip001** | 2, 4, 7, 8, 13 | 0001, 3515, 6661, 2902, 7361 |
| **kd001** | 3, 14, 15, 16, 17 | 5552, 2701, 3103, 3875, 5550 |

其余 7 个已登录号 **无代理** → 混合模式走 **手机 Worker**，不参与本次 A/B。

---

## 二、明天时间线（自动）

| 时刻 | 任务 | 说明 |
|------|------|------|
| **07:00** | Token 巡检 | 定时任务 |
| **08:53** | `daily_reserve` | 10 个绑代理账号服务器预约（hybrid） |
| **09:00** | 申购窗开启 | `sessionId` 由 0 变为有效 |
| **09:05 / 09:10 / 09:15** | 波次捡漏 | 仅重试失败项（`wave_retry_failed_only`） |
| **09:08** | **cron A/B H5 抢购** | `tomorrow_ab_test.py run --rush-only` |

```cron
8 9 * * * cd /opt/maotai && .venv/bin/python3 scripts/tomorrow_ab_test.py run --rush-only >> /opt/maotai/data/ab_test.log 2>&1
```

---

## 三、已就绪项 ✅

- [x] `H5_ACT_ID=86298`（Reqable 抓包，飞天 H5 页）
- [x] Shield + WASM 自检通过
- [x] 商品 id=1 `10941` 已改回 **`reserve`**（8:53 预约不误走 H5）
- [x] `rush.enabled: true`，抢购 10 次连打、间隔 0.5s
- [x] `shop_strategy: min_competition`，`shop_scope: province`
- [x] `maotai-api` / `nginx` 运行中
- [x] A/B 脚本 `/opt/maotai/scripts/tomorrow_ab_test.py`

---

## 四、已知风险 ⚠️（00:22 刚测）

1. **⚠️ 两组代理当前均 407（认证失败）**  
   `00:22` 复测：ip001（91HTTP）、kd001（快代理）都 `407 Proxy Authentication Required`，**服务器预约/抢购今晚跑不通**。  
   → **明天 8:53 前务必**：登录 91HTTP 控制台确认账密/白名单，更新 `config.yaml` 的 `proxy_pools.ip001`；快代理同理修 kd001。  
   → 修好后执行：`cd /opt/maotai && .venv/bin/python3 scripts/test_91http_proxy.py`

2. **快代理 kd001 即使修好也偏 IDC**  
   历史上对 i茅台 适配差；**91HTTP 修通是明天 A/B 有意义的前提**。

2. **9:08 才跑 H5 抢购**  
   比 9:00 晚 8 分钟；若需准点抢购，可改 cron 为 `0 9 * * *` 或手动 `run --rush-only --wait`。

3. **sessionId=0 属正常**  
   9 点前试跑门店列表 404 / sessionId=0，不是代理坏了。

4. **腾讯云 443 未放行**  
   管理 App HTTPS 登录需安全组开 TCP 443（实例 `ins-c3w6o73b`）。

---

## 五、明天你看结果（不用早起操作）

### 9:15 后 SSH 或 Web 查看

```bash
# 预约 + 抢购 A/B 报告
cat /opt/maotai/data/ab_test_report.json

# H5 抢购 cron 日志
tail -100 /opt/maotai/data/ab_test.log

# 代理对比历史
cat /opt/maotai/data/proxy_compare_report.json | tail -50
```

**Web 管理端：** 预约记录、任务日志、Dashboard 出口健康。

### 手动补跑（若 cron 失败）

```bash
cd /opt/maotai
# 只看分组
.venv/bin/python3 scripts/tomorrow_ab_test.py plan

# 补跑预约 A/B
.venv/bin/python3 scripts/tomorrow_ab_test.py run --reserve-only

# 补跑 H5 抢购 A/B（9 点窗内）
.venv/bin/python3 scripts/tomorrow_ab_test.py run --rush-only
```

---

## 六、业务员侧（可选）

- 7 个 **无代理** 账号：手机 App **等到 9 点 · 本机预约**（4G，关 Wi-Fi）
- 10 个 **A/B 账号**：已由服务器执行，**不要在 App 重复预约**
- 发码/登录仍在手机 4G，不经服务器

---

## 七、预期结论怎么读

| 现象 | 解读 |
|------|------|
| ip001 预约成功、kd001 全失败 | 91HTTP 可用，快代理需修白名单/密码 |
| 两组都 429 | 出口仍被风控，减并发或换住宅代理 |
| H5 抢购 `skipped` | 检查 `deploy/91http.env` 的 `H5_ACT_ID` |
| 预约成功、H5 全失败 | act_id 过期或不在抢购时段，需重新抓包 |

---

**明天测试我会按这份备忘执行；你 9:15 后看 Web 或把 `ab_test.log` 发我即可。**
