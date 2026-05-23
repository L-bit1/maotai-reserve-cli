# IP 隔离部署指南（1000 号 / 同一 Wi‑Fi 场景）

## 一、要解决什么问题

1000 个账号若都从 **同一条 Wi‑Fi 的同一个公网 IP** 访问 `app.moutai519.com.cn`，平台会看到：

- 短时间大量发验证码、登录、预约  
- 易 **HTTP 429**、验证码发不出、Token 失效、关联风控  

**IP 隔离** = 让不同批次的账号走 **不同公网出口**，而不是都挤在你家路由器那一个 IP 上。

> 本软件已支持：每个账号 `proxy_url` 或 `egress_group` + `config.yaml` 里的 `proxy_pools`。

---

## 二、三种做法（按推荐顺序）

### 做法 A：多手机热点（无代理费，适合几十～一两百号）

```text
调度电脑（只跑脚本，不连主 Wi‑Fi 发 1000 号）
    │
    ├── 手机1 开热点 → 账号 001～020（4G IP-1）
    ├── 手机2 开热点 → 账号 021～040（4G IP-2）
    └── …
```

**步骤：**

1. 准备 N 部手机（或轮开热点），每部 **开个人热点**。  
2. 电脑/树莓派用 **USB 网卡或 Wi‑Fi** 分别连不同热点（或分多台小机器，每台连一个热点）。  
3. 在 `config.yaml` 里为每个热点配一个 `proxy_pools` 项（见下文），或每台机器只放 20 个号的 `credentials.json` 直连该热点。  
4. 每组约 **10～30 号**，不要 1000 号共用一个热点。

**1000 号粗算：** 每 20 号 1 个出口 → 需要约 **50 个不同公网 IP**（50 张卡/50 次热点/50 条宽带或代理）。

---

### 做法 B：HTTP/SOCKS5 代理池（适合上百～1000 号，一台调度机）

在 `config.yaml` 配置 **出口组 → 代理地址**：

```yaml
# 每 20 个号一组时，1000 号需要 50 个代理
proxy_pools:
  ip001: "http://user:pass@1.2.3.4:8080"
  ip002: "http://user:pass@5.6.7.8:8080"
  ip003: "socks5://user:pass@9.10.11.12:1080"
  # … 共 50 项

max_accounts_per_egress: 20   # 文档建议值，分配脚本用
account_stagger_seconds: 1
egress_group_stagger_seconds: 3
```

在 `data/credentials.json` 每个账号写：

```json
"egress_group": "ip001"
```

或单账号写死代理（不用池子）：

```json
"proxy_url": "http://user:pass@1.2.3.4:8080"
```

**批量分组：**

```bash
cd "/Users/mac/Desktop/工作 /软件/茅台抢单软件"
python scripts/assign_egress_groups.py --per-group 20
# 先预览: 加 --dry-run
```

然后按脚本提示，在 `proxy_pools` 里补全 `ip001`～`ip050` 的代理地址。

---

### 做法 C：多台 Worker 分机部署（合同级）

```text
中心（二期后端） → 任务队列
    ├── Worker-A（宽带1）跑账号 1～250
    ├── Worker-B（宽带2）跑账号 251～500
    └── …
```

每台 Worker 本机 **直连当地宽带**，账号文件只放该出口的号；无需代理，但机器/线路要多。

---

## 三、软件里怎么生效

1. 启动预约时，`IMaotaiClient` 会读取该账号的 `proxy_url` 或 `egress_group` → `proxy_pools`。  
2. **登录、发码、预约、拉门店** 全部走该代理（`requests.Session.proxies`）。  
3. 日志会打印：`138****8000 出口 [ip003] 代理 http://user:***@host:port`  
4. 换出口组时多等 `egress_group_stagger_seconds` 秒（默认 2）。

**验证代理是否生效：**

```bash
# 用与 proxy_pools 相同的代理测试
curl -x "http://user:pass@host:port" https://api.ipify.org
```

---

## 四、1000 号 + 同一 Wi‑Fi 的务实方案

| 阶段 | 做法 |
|------|------|
| **试点** | 主 Wi‑Fi 上只跑 **30～50 号**，看 429 比例 |
| **扩容** | `assign_egress_groups.py --per-group 20` → **50 组** |
| **出口** | 至少 **20～50 个不同公网 IP**（热点/代理/多宽带），**不要** 1000 号共 1 IP |
| **登录** | 分天、分 IP 登录；**禁止** 1 个 IP 10 分钟内给几百号发验证码 |
| **预约** | 保留 `prewarm_minutes`、`wave_times`、错峰 |

同一 Wi‑Fi **可以** 作为「办公室网络」让电脑上网，但 **1000 个号的 i茅台 请求** 应走 `proxy_pools`，而不是直连这条 Wi‑Fi。

---

## 五、代理格式

| 类型 | 示例 |
|------|------|
| HTTP | `http://user:pass@host:8080` |
| HTTPS | `https://user:pass@host:8080` |
| SOCKS5 | `socks5://user:pass@host:1080` |
| 无认证 | `http://host:8080` |

需安装 SOCKS 依赖时：`pip install requests[socks]`（PySocks）。

---

## 六、登录与预约节奏（防 429）

| 操作 | 建议 |
|------|------|
| 发验证码 | 每 IP **每分钟 ≤ 3～5 次** |
| 登录 | 失败 429 后 **等待 45～90 秒**（程序已退避） |
| 预约 | `account_stagger_seconds: 1`；组间 `egress_group_stagger_seconds: 3` |
| 9:00 高峰 | `prewarm_minutes: 5` + 波次捡漏 |

---

## 七、合规提醒

- 使用代理请遵守服务商与 **i茅台用户协议**。  
- 勿用劣质机房代理批量作弊，易封号。  
- IP 隔离只提高 **预约提交成功率**，**不保证中签**。

---

## 八、相关文件

| 文件 | 说明 |
|------|------|
| `config.example.yaml` | `proxy_pools` 示例 |
| `data/credentials.json` | `egress_group` / `proxy_url` |
| `scripts/assign_egress_groups.py` | 批量分组 |
| `src/proxy_util.py` | 代理解析 |

---

*更新：2026-05-20*
