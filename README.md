# RealTimeCollabDoc

基于 Python FastAPI + Vue 3 的实时协作文档系统。支持多人实时编辑、文档内聊天、在线用户列表、快照与版本恢复、分享链接访问控制，并集成 Ollama 本地大模型的 AI 助手。

## Features

- JWT 认证：注册 / 登录 / 接口鉴权
- 文档管理：创建、编辑、删除、列表、快照与版本恢复
- 实时协作：WebSocket + 操作转换（OT），多人同时编辑同一文档
- 文档内聊天与在线用户实时列表
- 分享链接：生成分享链接，支持只读 / 可编辑权限控制
- AI 助手：集成 Ollama 本地大模型（默认 `granite4.1:8b`），可在文档内对话
- 子路径部署：支持 Nginx 反向代理挂载在 `/new/` 路径

## Tech Stack

- Backend: Python 3.11+ / FastAPI / SQLAlchemy 2 / WebSocket / python-jose / bcrypt
- Frontend: Vue 3 / TypeScript / Vite / Pinia / Element Plus
- Database: MySQL 8
- Deployment: Docker Compose + Nginx

## Project Structure

```text
collab-doc-project/
|- python-backend/       # FastAPI 后端（端口 8082）
|- frontend/             # Vue 3 + Vite 前端（开发端口 3000）
|- docs/                 # 设计文档
|- docker-compose.yml    # MySQL + 后端 + 前端一键部署
|- run.sh                # 启动脚本（优先使用 Docker Compose）
|- start-docker-8083.bat # Windows 快捷启动脚本
|- README.md
|- LICENSE
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- MySQL 8（本地创建数据库 `collab_doc`）

### Backend

```bash
cd python-backend
pip install -r requirements.txt
export DATABASE_URL="mysql+pymysql://root:your-password@127.0.0.1:3306/collab_doc"
python run.py
```

后端运行在 `http://127.0.0.1:8082`，API 前缀为 `/api`。

### Frontend

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://127.0.0.1:3000`，开发环境通过 Vite 代理转发 `/new/api` 到后端（可用 `VITE_PROXY_TARGET` 覆盖目标地址）。

## Docker Compose Deployment

```bash
export MYSQL_ROOT_PASSWORD="your-mysql-password"
export APP_JWT_SECRET="replace-with-a-long-random-secret"
./run.sh
```

或直接：

```bash
docker compose up -d --build
```

端口映射（可通过环境变量覆盖）：

| Service  | Host Port | Container Port |
|----------|-----------|----------------|
| MySQL    | 3308      | 3306           |
| Backend  | 8082      | 8082           |
| Frontend | 3000      | 80 (Nginx)     |

## Test Accounts

初始化时自动创建演示账号，默认密码均为 `password123`：

- `admin`
- `user1`
- `user2`

## Sub-path Deployment

如需与其他项目共用域名（例如挂载在 `http://<host>/new/`），需同步修改三处配置，否则会出现空白页或 API 被拦截：

1. `frontend/vite.config.ts` — 构建 `base: '/new/'`
2. `frontend/src/router/index.ts` — `createWebHistory('/new/')`
3. `frontend/src/api/config.ts` — API 请求路径加 `/new` 前缀

构建产物 `frontend/dist/` 已预构建提交，部署时直接由 Nginx 提供静态文件。

## License

[MIT](LICENSE)
