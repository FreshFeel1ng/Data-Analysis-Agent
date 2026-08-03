# Data Analysis Agent

AI 驱动的智能数据分析平台。用自然语言向数据库提问，自动生成 SQL 并执行，返回数据表格 + ECharts 交互式图表 + 分析报告。

## 核心功能

| 能力 | 说明 |
|------|------|
| **Text-to-SQL** | 自然语言 → SQL → 执行 → 表格展示 |
| **可视化** | LLM 生成 ECharts 配置 JSON，前端 Canvas 渲染 |
| **一键训练** | 从 INFORMATION_SCHEMA 自动提取 DDL + 文档 |
| **自学习** | 每次成功工具调用存入 Milvus，类似问题自动参考历史 |
| **多图表** | 一次查询同时显示柱状图 + 饼图等多个图表 |
| **审计追踪** | 完整记录 user / tool / resource / time |
| **权限控制** | admin / analyst 角色，工具级权限 |
| **下载导出** | CSV(UTF-8 BOM) / PNG / Markdown 报告 |
| **敏感数据保护** | SQL 结果敏感字段自动脱敏（phone / email 等） |
| **多数据源** | PostgreSQL + MySQL |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| AI 编排 | LangGraph |
| 大模型 | DeepSeek V4（兼容 OpenAI API） |
| 嵌入模型 | BAAI/bge-small-zh-v1.5（本地，512 维） |
| 向量库 | Milvus |
| 业务数据库 | PostgreSQL |
| 目标数据库 | PostgreSQL / MySQL |
| 图表 | Apache ECharts |
| 前端 | React + React Router + ReactMarkdown |

## 项目结构

```
Data-Analysis-Agent/
├── backend/                         # FastAPI 后端
│   ├── app/
│   │   ├── main.py                  # 应用入口 + CORS + 生命周期
│   │   ├── config.py                # 全局配置（Pydantic Settings）
│   │   ├── database.py              # PostgreSQL 异步连接 + 自动建表
│   │   ├── models/                  # SQLAlchemy ORM 模型
│   │   │   ├── user.py              # 用户（admin/analyst）
│   │   │   ├── audit.py             # 审计日志
│   │   │   ├── training.py          # 训练数据（DDL/Schema/文档/SQL示例）
│   │   │   ├── db_connection.py     # 数据源连接配置
│   │   │   └── query_history.py     # 完整查询历史
│   │   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── core/                    # 核心模块
│   │   │   ├── auth.py              # JWT + bcrypt 认证
│   │   │   ├── permissions.py       # RBAC 权限控制
│   │   │   └── audit.py             # 审计日志记录
│   │   ├── agent/                   # LangGraph AI Agent
│   │   │   ├── graph.py             # StateGraph 工作流（核心）
│   │   │   ├── tools.py             # 工具注册表（SQL执行/图表/检索）
│   │   │   └── prompts.py           # LLM 提示词
│   │   ├── services/                # 业务服务
│   │   │   ├── db_service.py        # 目标数据库连接管理
│   │   │   ├── milvus_service.py    # 向量存储 + 语义检索
│   │   │   └── training_service.py  # 训练数据上下文构建
│   │   └── api/                     # REST API 路由
│   │       ├── auth.py              # 注册/登录/用户管理
│   │       ├── query.py             # Text-to-SQL 核心入口
│   │       ├── training.py          # 训练数据 CRUD + 自动导入
│   │       ├── connections.py       # 数据源管理
│   │       └── history.py           # 查询历史 + 删除
│   ├── environment.yml              # Conda 环境
│   ├── requirements.txt             # Pip 依赖
│   └── run.py                       # 启动入口
├── frontend/                        # React 前端
│   └── src/
│       ├── components/
│       │   ├── SqlQuery.js           # SQL 查询（表格 + ECharts + 下载）
│       │   ├── History.js            # 历史记录（展开详情 + 图表回显）
│       │   ├── Training.js           # 训练管理（4 种模式）
│       │   ├── Connections.js        # 数据源连接管理
│       │   └── Sidebar.js            # 导航栏 + 用户信息
│       ├── pages/
│       │   ├── LoginPage.js          # 登录 + 注册
│       │   └── MainPage.js           # 主页面路由
│       └── styles/global.css         # 全局样式
├── docker-compose.yml               # 后端 + 前端编排
└── .gitignore
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- PostgreSQL（运行中）
- Milvus（运行中，可选）
- DeepSeek API Key

### 1. 创建数据库

```sql
CREATE DATABASE data_agent;
```

### 2. 后端启动

```bash
# 创建 Conda 环境
cd backend
conda env create -f environment.yml
conda activate data-agent

# 安装依赖（国内镜像）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置环境变量
copy .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 启动
python run.py
```

API 文档：http://localhost:8000/docs

### 3. 前端启动

```bash
cd frontend
npm install
npm start
```

前端页面：http://localhost:3000

### 4. 使用流程

1. 打开 http://localhost:3000 → 注册账号 → 登录
2. 进入「数据源」→ 添加 PostgreSQL/MySQL 连接
3. 进入「训练管理」→ 选择数据源 → **自动导入 Schema**
4. 进入「SQL 查询」→ 输入问题 → 查看结果

### 示例问题

```
"查询各季度销量变化，画出柱形图"
"统计各产品销售额占比，画出饼图"
"分析每月订单趋势，画出折线图"
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|------|
| `LLM_PROVIDER` | 大模型：deepseek / openai | deepseek |
| `LLM_MODEL` | 模型名称 | deepseek-chat |
| `LLM_API_KEY` | API 密钥 | - |
| `LLM_BASE_URL` | API 端点 | https://api.deepseek.com/v1 |
| `EMBEDDING_PROVIDER` | 嵌入模型：local / openai | local |
| `EMBEDDING_MODEL` | 嵌入模型名称 | BAAI/bge-small-zh-v1.5 |
| `POSTGRES_*` | 业务数据库连接 | localhost:5432 |
| `MILVUS_*` | 向量数据库连接 | localhost:19530 |

## 数据库表

| 表名 | 用途 |
|------|------|
| `users` | 用户认证 + 角色 |
| `audit_logs` | 操作审计日志 |
| `training_data` | DDL / Schema / 文档 / SQL 示例 |
| `db_connections` | 目标数据库连接配置 |
| `query_history` | 完整查询历史（含 SQL / 图表 / 结果） |

## 架构

```
用户输入自然语言问题
        │
        ▼
┌─────────────────────────────────────────┐
│              FastAPI 后端                │
│                                         │
│  JWT 认证 → 权限校验                     │
│       ↓                                 │
│  加载训练数据（DDL / Schema）             │
│       ↓                                 │
│  Milvus 语义检索历史成功案例              │
│       ↓                                 │
│  LangGraph Agent                        │
│  ├─ execute_sql       ← DeepSeek 决策   │
│  ├─ get_schema                         │
│  └─ generate_chart                     │
│       ↓                                 │
│  敏感字段脱敏 → 审计日志 → 自学习存储     │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│              React 前端                  │
│                                         │
│  登录/注册 → 主界面                      │
│  ├─ SQL 查询（表格 + ECharts 图表）      │
│  ├─ 历史记录（展开详情 + 下载）           │
│  ├─ 训练管理（4 种模式）                 │
│  └─ 数据源管理                          │
└─────────────────────────────────────────┘
```

## 自学习机制

```
查询成功
    │
    └─ 工具调用记录 → 向量化 → 存入 Milvus

下次类似问题
    │
    └─ Milvus 语义检索 → Top 5 成功案例 → 注入 Prompt
                                            ↓
                               DeepSeek 参考历史选择工具
```

## 训练模式

| 模式 | 说明 |
|------|------|
| DDL 语句 | 直接提供 CREATE TABLE 建表语句 |
| 数据库 Schema | 自动导入 INFORMATION_SCHEMA.COLUMNS |
| 文档 | 业务术语、指标定义等补充说明 |
| SQL 示例 | 正确的、带自然语言描述的 SQL 查询 |

## 权限模型

| 工具 | admin | analyst |
|------|------|---------|
| execute_sql | ✅ | ✅ |
| get_schema | ✅ | ✅ |
| generate_chart | ✅ | ✅ |
| add_training_data | ✅ | ❌ |
| manage_db_connection | ✅ | ❌ |
| manage_users | ✅ | ❌ |

## Docker（可选）

```bash
docker compose up -d
```
