# 服务器部署文件

完整说明见 [docs/服务器选购与部署指南.md](../docs/服务器选购与部署指南.md)。

## 一键部署（Ubuntu + IP 访问）

```bash
export DEPLOY_HOST=你的服务器IP
export DEPLOY_USER=ubuntu
export DEPLOY_PASS='SSH密码'
export MT_ADMIN_PASSWORD='管理后台强密码'
./scripts/deploy_paramiko.sh   # 或: .venv/bin/python scripts/deploy_paramiko.py
```

部署后访问 `http://IP/`，API 文档 `http://IP/api/v1`（Swagger 在 `/docs`）。

## 快速步骤

```bash
# 1. 服务器安装依赖后，代码放到 /opt/maotai

# 2. 配置
cp deploy/.env.example deploy/.env
vim deploy/.env
cp config.example.yaml config.yaml
vim config.yaml

# 3. 构建前端
cd web && npm install && npm run build

# 4. API 服务
sudo cp deploy/maotai-api.service /etc/systemd/system/
sudo systemctl enable --now maotai-api

# 5. Nginx
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/maotai
# 编辑 server_name、ssl
sudo ln -sf /etc/nginx/sites-available/maotai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d 你的域名.com
```

## 生产前端 API 地址

构建前在 `web/.env.production` 写入：

```env
VITE_API_BASE_URL=/api/v1
```

使用 Nginx 同域反代时保持 `/api/v1` 即可。
