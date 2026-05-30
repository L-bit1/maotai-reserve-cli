# 茅台抢单软件

i茅台 **预约申购** CLI 工具（个人学习研究用）。支持多账号、定时提交、门店策略、本地加密存储。

📄 **完整介绍文档**：[docs/介绍文档.md](docs/介绍文档.md)（产品说明、安装、使用、验收建议、FAQ）  
📱 **没有安卓机**：[docs/无安卓真机指南.md](docs/无安卓真机指南.md)（Mac 模拟器 / iPhone 抓包）  
📋 **当下进度（2.5周开发+2.5周调试）**：[docs/进度报告-五周计划.md](docs/进度报告-五周计划.md)  
📋 **五周进度复盘**：[docs/五周进度报告.md](docs/五周进度报告.md)  
🔌 **前后端接口方案**：[docs/前后端接口方案.md](docs/前后端接口方案.md)（二期 Web + API）  
🖥️ **Web 管理端**：[docs/Web管理端使用说明.md](docs/Web管理端使用说明.md)（`backend/` + `web/`）  
💰 **项目费用估算**：[docs/项目费用估算.md](docs/项目费用估算.md)（前后端分项报价）  
🖧 **服务器选购与部署**：[docs/服务器选购与部署指南.md](docs/服务器选购与部署指南.md) | [deploy/README.md](deploy/README.md)  
📈 **抢茅台优化策略**：[docs/抢茅台优化策略.md](docs/抢茅台优化策略.md)（网易/ken 脚本对照）  
🌐 **IP 隔离部署**：[docs/IP隔离部署指南.md](docs/IP隔离部署指南.md)（代理/热点/1000 号分组）

> **说明**：i茅台为预约 + 抽签机制，本工具仅辅助**提交预约**，不保证中签。请遵守官方用户协议与当地法律法规。

## 功能

- **Android 客户端**（`android-app/`）：手机绑号、预约、查中签，连接云服务器 API
- **Web 管理端**（Vue3）：账号 / 商品 / 任务 / 记录 / **中签与付款** / 设置
- **中签查询**、**待付款汇总**、PushPlus 提醒（支付须在 i茅台 App 内完成）
- **周末欢乐购**、**小茅运旅行**
- 交互式 CLI（Rich 界面，菜单 8～10 对应上述能力）
- 手机号 + 短信验证码登录
- 收货地址 / 门店策略（库存优先、距离优先）
- 定时预约（默认申购窗口前提交）
- 试跑模式（`--dry-run`）
- 多账号、本地加密凭证

## 环境

- Python 3.10+
- macOS / Linux

## 快速开始

```bash
# 克隆后
cp config.example.yaml config.yaml
# 编辑 config.yaml：secret_key、amap_key（可选）

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python cli.py          # 交互菜单（推荐）
# 或双击 macOS：启动茅台抢单.command
```

首次使用：菜单 **1** 配置账号与地址 → **5** 健康检查 → **3** 试跑。

### Web 管理端（二期）

```bash
./scripts/start-api.sh   # 终端1 → http://127.0.0.1:8000/docs
./scripts/start-web.sh   # 终端2 → http://127.0.0.1:5173  默认 admin / admin123
```

## 命令

| 命令 | 说明 |
|------|------|
| `python cli.py` | 交互主菜单 |
| `python check.py` | 健康检查 |
| `python main.py --dry-run` | 试跑（不提交） |
| `python main.py` | 正式预约 |

## 免责声明

本项目仅供学习交流，请勿用于商业或违规用途。使用后果由使用者自行承担。

## License

MIT
