# Web 管理端使用说明

基于 [前后端接口方案.md](./前后端接口方案.md) 实现的 **网页版管理后台**（后期可复用 API 做手机 App）。

## 目录结构

```text
backend/     FastAPI 管理 API（端口 8000）
web/         Vue3 + Element Plus（端口 5173）
```

## 服务器定时任务（无需手动点预约）

后端启动后会自动注册（`MT_SCHEDULER_ENABLED=true` 时）：

| 任务 | 默认时间 | 说明 |
|------|----------|------|
| 每日申购 | 约 8:54（按 config 预热提前） | 调用完整 `execute_reserve`（含 9 点等待与捡漏波次） |
| 中签同步 | 18:03 | 写入数据库，有待付款时 PushPlus 通知 |
| Token 巡检 | 07:00 | 异常账号 PushPlus 提醒 |
| 周末欢乐购 | 周日 15:05 | 可选 `MT_WEEKEND_RESERVE_ENABLED=false` 关闭 |

在 **仪表盘** 或 **设置 → 健康检查** 可查看下次执行时间。

## 批量导入账号

Web **账号管理** 页支持上传 CSV，示例见 `docs/accounts-import.example.csv`。导入后请在页面逐号 **发码 → 登录** 获取 Token。

## 启动步骤

### 1. 准备环境

```bash
cd "/Users/mac/Desktop/工作 /软件/茅台抢单软件"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r backend/requirements.txt
```

确保已有 `config.yaml`（可从 `config.example.yaml` 复制）。

### 2. 一键启动（推荐，避免 500）

```bash
cd "/Users/mac/Desktop/工作 /软件/茅台抢单软件"
chmod +x scripts/start-all.sh
./scripts/start-all.sh
```

或双击 **`启动Web+API.command`**（会同时起 API + Web）。

> **只运行 `start-web.sh` 而不起后端时**，页面会报 `Request failed with status code 500`（Vite 代理连不上 8000 端口）。

### 3. 分终端启动（可选）

**终端 1 — 后端：**

```bash
./scripts/start-api.sh
```

- API：http://127.0.0.1:8000/api/v1  
- 文档：http://127.0.0.1:8000/docs  

**终端 2 — 前端：**

```bash
./scripts/start-web.sh
```

浏览器打开：http://127.0.0.1:5173  

默认管理员：**admin / admin123**（生产请设置 `MT_ADMIN_PASSWORD`）。

开发环境已通过 Vite 代理 `/api` → `8000`，无需单独配置 CORS。

## 页面功能

| 页面 | 功能 |
|------|------|
| 登录 | 管理端 JWT 登录 |
| 仪表盘 | 预约统计、最近任务 |
| 账号管理 | 增删改、发码、短信登录、Token 校验 |
| 商品管理 | 商品编码维护 |
| 门店排行 | 库存 Top、同步门店 |
| 任务中心 | 创建/试跑/执行预约任务 |
| 预约记录 | 历史记录与成功率 |
| 系统设置 | 修改 config.yaml、健康检查 |

## 与一期 CLI 的关系

- 启动 API 时会自动把 `data/credentials.json` 同步到 SQLite。  
- 在 Web 登录账号后会写回 `credentials.json`，CLI 仍可使用。  
- i茅台 `MT-Token` **不会**下发到浏览器，仅存服务端。

## 手机端（后期）

当前为响应式 Web（`viewport` + 移动端表格适配），后续可用同一套 `/api/v1` 开发：

- uni-app / Flutter / 原生 App  
- 仅需实现管理端或精简版（账号 + 任务 + 推送）

## 环境变量（可选）

| 变量 | 说明 |
|------|------|
| `MT_ADMIN_USERNAME` | 管理员用户名 |
| `MT_ADMIN_PASSWORD` | 管理员密码 |
| `MT_SECRET_KEY` | JWT 密钥 |
| `MT_CORS_ORIGINS` | 额外 CORS 源 |

---

*2026-05-20*
