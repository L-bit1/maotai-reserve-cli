# Trae 与 Cursor 协作说明

> **给 Trae 的第一句话**：本仓库 Git 只公开文档，但**完整源码在同一文件夹的磁盘上**。你必须打开本地目录改代码，不要只读 README 就下结论。

---

## 0. Trae 要能改代码 — 必做一步

在 **Trae IDE** 中：

1. **File → Open Folder**
2. 选择：`/Users/mac/Desktop/工作 /软件/茅台抢单软件`
3. 确认左侧能看到 `src/`、`backend/`、`android-app/`（不是只有 `docs/`）

若 Trae 仍说「没有 .py」：在对话里粘贴：

```text
工作区根目录是 /Users/mac/Desktop/工作 /软件/茅台抢单软件
请直接读取并修改 src/ backend/ android-app/ scripts/ 下的文件
不要依赖 Git 索引；Git 故意只跟踪 docs/
先读 docs/Trae与Cursor协作说明.md 和 docs/AI变更记录.md
```

---

## 1. 为什么 Trae 曾误判「无源码」

| Trae 常见误区 | 事实 |
|---------------|------|
| 只索引 Git | `.gitignore` 首行 `*` → Git 里 **0 个 .py** |
| 只读 README | README 描述 **公开仓库**，不是本机交付包 |
| 正确做法 | **打开本地文件夹**，与 Cursor 同一路径 |

---

## 2. 双 AI 改代码 — 推荐分工

两者**都可以改代码**；按模块分工，减少撞车：

| 模块 | 优先负责 | 说明 |
|------|----------|------|
| `android-app/` | Trae 或 Cursor | App UI、本机直购、登录 |
| `backend/` | Trae 或 Cursor | API、定时任务、mobile 接口 |
| `src/` | 共用 | i茅台协议、Shield、h5_rush |
| `web/` | Trae | 管理端页面（可选） |
| `scripts/` 部署 | **Cursor** | SSH、APK 上传（Trae 也可写脚本） |
| `docs/` | **Trae** | 客户文档、汇报、SOP |
| **部署到 139.155.134.97** | **Cursor**（或你手动） | 改完 code 需有人执行 deploy |

同一文件**不要两个 AI 同时改**。换工具前先让对方停，或你保存/同步一次。

---

## 3. 交接规则（防互相覆盖）

1. **改代码前**：读 [`docs/AI变更记录.md`](./AI变更记录.md) 最新几条  
2. **改代码后**：在 `AI变更记录.md` **追加一行**（时间、工具、改了啥、是否部署）  
3. **换 AI 前**：保存所有文件；你说一句「Trae 刚改完 backend，Cursor 请部署」  
4. **禁止**：Trae 改一半不记录 → Cursor 覆盖  
5. **生产密钥**：`config.yaml`、`deploy/.env`、SSH 密码 **不进 Git、不在文档写明文**

---

## 4. 每次开 Trae 对话 — 粘贴这段

```text
【Trae 开发模式】

工作区：/Users/mac/Desktop/工作 /软件/茅台抢单软件
你可以直接读写 src/ backend/ android-app/ web/ scripts/
先读：docs/Trae与Cursor协作说明.md、docs/AI变更记录.md

生产：139.155.134.97  /opt/maotai/
KPI：20:00 手机 4G H5 直购 10941，分片 phone-01
App 1.8.7 已部署；5 个号待手机本机登录

改完代码请更新 docs/AI变更记录.md
部署由 Cursor 或我手动 SSH 执行
```

---

## 5. 每次开 Cursor 对话 — 粘贴这段

```text
【Cursor 开发/部署模式】

Trae 可能也在改同一仓库，请先读 docs/AI变更记录.md
工作区：/Users/mac/Desktop/工作 /软件/茅台抢单软件
SSH：ubuntu@139.155.134.97（密码见交付文档）

若 Trae 刚改了代码，请 review  diff 再部署，避免覆盖
```

---

## 6. 源码结构速查

```text
src/              # 协议、Shield、h5_rush、runner
backend/          # FastAPI、scheduler、mobile API
web/              # Vue 管理端
android-app/      # 管理 App 1.8.7
scripts/          # 部署、巡检、act_id
deploy/           # systemd、nginx
config.yaml       # 本地配置（Git 忽略）
```

---

## 7. Trae 改代码时的规范

- 跟现有风格走，小步改，别大重构  
- 改 `backend/` 或 `src/` 后，在 `AI变更记录.md` 注明是否要 **restart maotai-api**  
- 改 `android-app/` 后注明是否要 **升 versionCode + 发 APK**  
- 不要删 `site_defaults.py` 里生产 IP/分片，除非用户要求  
- 业务逻辑见 `docs/20点直购失败决策树.md`

---

## 8. 可选：让 Git 也跟踪源码（仅私有仓库）

若 Trae 强依赖 Git 索引，可把仓库改为 **GitHub Private**，再改 `.gitignore` 放开 `src/`、`backend/` 等。  
**公开仓库不要这样做。**

本地临时强制跟踪单个文件：

```bash
git add -f backend/app/api/v1/mobile.py
```

---

## 9. 当前生产状态

| 项 | 状态 |
|----|------|
| 服务器 API | ✅ 139.155.134.97 |
| App | 1.8.7，APK 已上传 |
| mobile 连打 | 48 次 + 补货波次（已部署） |
| 阻塞 | 5 号无 Token，需手机 4G 本机登录 |

*维护：任一 AI 部署或重大变更后更新本节日期*

---

## 10. 好想法怎么互传（Trae ↔ Cursor）

**核心**：不要只在聊天里说一句就忘——写入 [`docs/AI想法池.md`](./AI想法池.md)，你当「传话筒」转一句即可。

### 你给 Trae 说什么（开场 + 能互传想法）

见下一节「复制即用话术」。

### Trae 有好点子 → 告诉 Cursor

1. Trae 在 `docs/AI想法池.md` 追加一行（ID 如 `T001`）
2. 你对 Cursor 说：

```text
Trae 提了一个想法，请先读 docs/AI想法池.md 的 T001，评估并实现（或说明为何不做的原因）
```

### Cursor 有好点子 → 告诉 Trae

1. Cursor 写入 `docs/AI想法池.md`（ID 如 `C001`）
2. 你对 Trae 说：

```text
Cursor 提了一个想法，请先读 docs/AI想法池.md 的 C001，你来改代码或写进 docs/
```

### 三种传话方式（任选）

| 方式 | 做法 | 适合 |
|------|------|------|
| **A. 想法池** | 写 `docs/AI想法池.md` | 正式、可追踪（推荐） |
| **B. 复制粘贴** | Trae 输出一段 → 你整段贴给 Cursor | 临时、快速 |
| **C. 变更记录** | 已决定要做 → 写 `AI变更记录.md` | 开始动手时 |

---

## 11. 复制即用话术

### 第一次让 Trae 进入项目

```text
请用 Trae 开发模式：

1. 打开文件夹：/Users/mac/Desktop/工作 /软件/茅台抢单软件
2. 先读 docs/Trae与Cursor协作说明.md、docs/AI变更记录.md、docs/AI想法池.md
3. 你可以直接改 src/ backend/ android-app/ 的代码
4. 有好想法请写入 docs/AI想法池.md（编号 T001…），我会转告 Cursor
5. 改完代码必须更新 docs/AI变更记录.md

当前最急：5 个号手机 4G 本机登录；20 点 H5 直购。
```

### 让 Trae 和 Cursor 对齐同一件事

```text
【同步任务】
目标：（例如：登录页只留密码）
Trae 负责：（例如：改 LoginScreen.kt）
Cursor 负责：（例如：部署 + 查服务器账号 Token）
完成后各自更新 AI变更记录.md
```

### 你当传话筒（最常用两句）

→ 给 **Cursor**：
```text
Trae 在 docs/AI想法池.md 写了 T00X，请读并实现。
```

→ 给 **Trae**：
```text
Cursor 在 docs/AI想法池.md 写了 C00X，请读并实现或补充文档。
```
