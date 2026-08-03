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

## RAG and Agent Workflow

The knowledge base is implemented as a local, deterministic RAG pipeline:

1. Documents are split into paragraph-aware chunks and stored in `document_chunks`.
2. Search filters documents by owner, public visibility, or explicit sharing permission.
3. The lexical retriever returns ranked chunks with document title, chunk index, score, and matched terms.
4. The LangChain Agent runs an LCEL pipeline: `retrieve_chunks -> route_evidence -> build_context -> generate_answer -> format_citations`.
5. If no evidence is retrieved, the Agent refuses to answer without calling Ollama.

API examples:

```text
GET  /api/ai/knowledge/search?q=collaboration&topK=8
POST /api/ai/agent/query
     {"question":"Which documents mention collaboration risks?","topK":6}
```

The first version uses lexical retrieval so it can run without a GPU or embedding model. The retriever can later be extended with embeddings and hybrid ranking without changing the frontend contract or Agent chain.

## Tech Stack

- Backend: Python 3.11+ / FastAPI / SQLAlchemy 2 / WebSocket / python-jose / bcrypt
- Agent: LangChain Core LCEL / PromptTemplate / RunnableBranch / local lexical retrieval / Ollama
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
export DATABASE_URL="mysql+pymysql://root:***@127.0.0.1:3306/collab_doc"
python run.py
```

后端运行在 `http://127.0.0.1:8082`，API 前缀为 `/api`。
Agent 的实时查询开箱即用：天气走 Open-Meteo（免费、无需 key），
网页/新闻搜索默认走 Bing（免费、无需 key）。可选配置
`TAVILY_API_KEY`（并设置 `WEB_SEARCH_PROVIDER=tavily`）可切换到
Tavily 搜索；未配置 key 时自动降级回 Bing，不会编造实时新闻。

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
export TAVILY_API_KEY="tvly-..."
./run.sh
```

或直接：

```bash
docker compose up -d --build
```

Docker deployment requires `APP_JWT_SECRET`; the backend refuses to start in
production when the development JWT secret is used. Compose also starts Ollama
and pulls `OLLAMA_MODEL` (default: `granite4.1:8b`) into the persistent
`ollama-data` volume. Agent live web/news search works out of the box:
weather uses Open-Meteo and web/news search defaults to Bing, both free
and key-less. Optionally set `TAVILY_API_KEY` (and
`WEB_SEARCH_PROVIDER=tavily`) to switch to Tavily; without the key the
Agent falls back to Bing instead of inventing current news.

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
