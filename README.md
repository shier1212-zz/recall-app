# Recall · AI 智能错题本

> 面向学生群体的 AI 错题管理平台：拍照 / 截图 / 文本 / 对话录入 → AI 自动归类学科知识点与错因 → 错题本管理 → 基于 SM-2 遗忘曲线的智能复习 → 数据看板与导出。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Frontend](https://img.shields.io/badge/frontend-Vue%203%20%2B%20Vite-42b883.svg)](frontend)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](backend)

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
  - [1. 后端](#1-后端)
  - [2. 前端](#2-前端)
  - [3. 配置 AI 供应商](#3-配置-ai-供应商)
  - [4. 安装 OCR（可选）](#4-安装-ocr可选)
- [运行项目](#运行项目)
- [功能与实现说明](#功能与实现说明)
- [API 接口一览](#api-接口一览)
- [数据与备份](#数据与备份)
- [项目文档](#项目文档)
- [目录结构](#目录结构)
- [后续路线](#后续路线)
- [许可证](#许可证)

---

## 项目简介

Recall 帮助学生把「做错的题」沉淀为可复习、可检索、可追踪的知识资产：

1. **多模态录入**：支持拍照 / 截图上传（OCR 识别）、纯文本粘贴、以及「对话式录入」（用自然语言描述错题，AI 识别并自动归档）。
2. **AI 结构化解析**：调用大模型自动抽取学科、知识点、错误原因，并写入向量库用于相似题召回。
3. **错题本管理**：按分类（学科 / 自定义错题本）组织，支持搜索、复习状态标记、删除。
4. **智能复习（SM-2）**：基于 Super Memo 2 遗忘曲线计算每道题的复习间隔与到期日，前端按「复习计划」推送到期题。
5. **数据看板**：总题量、已复习、待复习、今日到期、学科分布、录入趋势等真实统计。
6. **导出**：一键导出 PDF（ReportLab，自带中文字体）或 Markdown 复习清单。

---

## 核心特性

- ✅ **多供应商 AI**：DeepSeek / 智谱 GLM / 硅基流动，每个供应商可独立填写 `base_url`、`api_key`、`model`，未配置时自动降级为规则回复，不报错。
- ✅ **流式答疑**：`/api/chat/stream` 边生成边返回，前端逐字渲染。
- ✅ **OCR 拍照识别**：PaddleOCR-VL，未安装时 `/api/ocr` 降级返回提示，不中断流程。
- ✅ **SM-2 记忆曲线**：`easiness_factor` / `interval_days` / `due_date` / `repetitions` 字段 + 排程算法。
- ✅ **向量相似题**：ChromaDB 持久化，录入时自动建索引，看板可召回相似题。
- ✅ **分页与校验**：列表支持 `limit/offset` 分页；录入接口对 `content` 非空、分类存在性做参数校验。
- ✅ **双模式前端**：`VITE_USE_MOCK=true` 时不依赖后端即可演示；`false` 时对接真实 FastAPI 后端。
- ✅ **导出**：PDF（中文） + Markdown。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS + vue-router + axios |
| 后端 | FastAPI + Uvicorn + SQLAlchemy + Pydantic |
| 数据库 | SQLite（`recall.db`）+ ChromaDB（向量） |
| AI | OpenAI 兼容协议（DeepSeek / 智谱 GLM / 硅基流动） |
| OCR | PaddleOCR-VL（可选，CPU 版） |
| 导出 | ReportLab（PDF） |

---

## 系统架构

```
┌─────────────────┐      HTTP /api      ┌──────────────────────────┐
│   Vue 3 前端      │ ─────────────────▶ │   FastAPI 后端             │
│  (Vite 5173)     │ ◀── JSON / Stream ─ │   (Uvicorn 8000)           │
└─────────────────┘                     └────────────┬─────────────┘
                                                     │
                          ┌──────────────────────────┼──────────────────────────┐
                          ▼                          ▼                          ▼
                   ┌────────────┐            ┌──────────────┐           ┌──────────────┐
                   │  SQLite     │            │  ChromaDB    │           │  大模型 API   │
                   │ (错题/分类) │            │ (向量相似题) │           │ DeepSeek/GLM  │
                   └────────────┘            └──────────────┘           └──────────────┘
                          ▲                          │
                          │                          ▼
                   ┌────────────┐            ┌──────────────┐
                   │ PaddleOCR  │            │  OCR Service │
                   │ (图片识别) │            └──────────────┘
                   └────────────┘
```

---

## 环境要求

- **Python** ≥ 3.12（开发环境使用 3.13，PaddlePaddle 3.x 已提供 cp313 轮子）
- **Node.js** ≥ 18（推荐 20+）
- 操作系统：Windows / macOS / Linux

---

## 快速开始

### 1. 后端

```bash
cd backend

# 创建并激活虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# （可选）配置 AI Key —— 也可在网页「设置」里填，无需改文件
cp .env.example .env

# 启动
uvicorn app.main:app --reload --port 8000
```

- 接口文档：http://localhost:8000/docs
- 首次启动自动建表并写入演示数据（`recall.db`）

### 2. 前端

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

- 默认 `VITE_USE_MOCK=true`：**不启动后端也能完整演示**。
- 对接真实后端：`frontend/.env` 中设 `VITE_USE_MOCK=false`（dev 下 `/api` 已代理到 8000）。

### 3. 配置 AI 供应商

两种方式（任选其一）：

- **网页填写（推荐）**：进入「AI 答疑 / 设置」页，选择供应商并填入 `api_key`、`base_url`、`model`，后端持久化到数据库。
- **环境变量**：复制 `backend/.env.example` 为 `backend/.env` 并填入（示例文件已留占位，不会提交真实密钥）。

> 未配置任何 Key 时，答疑 / 解析接口会自动降级为规则回复，便于离线演示。

### 4. 安装 OCR（可选）

拍照识别需要 PaddleOCR。CPU 版安装：

```bash
cd backend
.venv\Scripts\activate
pip install paddlepaddle paddleocr
```

> 不安装也能跑：此时 `/api/ocr` 返回降级提示，前端可手动输入文本，流程不中断。

---

## 运行项目

### 一键启动（Windows）

依赖装好一次后，日常启动只需双击：

- `start.bat`：启动后端（8000）+ 前端（5173）并打开浏览器
- `stop.bat`：按端口停止前后端服务

### 手动启动

开两个终端，分别运行「后端」「前端」小节中的 `uvicorn` 与 `npm run dev`。

---

## 功能与实现说明

- **AI 降级策略**：DeepSeek / PaddleOCR 未配置时接口不报错，返回降级结果，前端可无缝演示与联调。
- **流式答疑**：`chat_service.chat_reply_stream` 为生成器，后端用 `StreamingResponse` 返回 `text/plain`，前端用 `fetch` + `ReadableStream` 边收边渲染。
- **SM-2 记忆曲线**：`review_mistake` 依据 `result` 更新 `easiness_factor` / `interval_days` / `due_date`；`mastered` 按公式推后，`unmastered` 降低 EF 并重置间隔，`skip` 不改变排程。`/api/review/plan` 返回今日到期题。
- **向量检索**：ChromaDB 持久化在 `backend/chroma_data`，首次使用默认 embedding 模型需联网下载；失败不影响主流程。
- **PDF 中文**：ReportLab 使用内置 CID 中文字体，无需额外字体文件。
- **参数校验**：录入接口对 `content` 非空、分类存在性返回 `422`；`review` 校验 `result` 枚举。

---

## API 接口一览

所有路由挂在 `/api` 前缀下。完整定义见后端 `app/routers/` 与各 `services/`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/api/categories` | 错题本（分类）列表 |
| POST | `/api/categories` | 新增错题本（持久化） |
| GET | `/api/mistakes?category_id=&q=&reviewed=&limit=&offset=` | 错题列表（过滤 + 分页） |
| POST | `/api/mistakes` | 录入错题（自动 AI 解析 + 写向量库） |
| PATCH | `/api/mistakes/{mid}/toggle-review` | 切换复习状态 |
| POST | `/api/mistakes/{mid}/review` | SM-2 复习（`result=mastered/unmastered/skip`） |
| GET | `/api/review/plan` | 到期复习计划 |
| DELETE | `/api/mistakes/{mid}` | 删除错题 |
| POST | `/api/ai/analyze` | 错题 AI 解析（学科 / 知识点 / 错因） |
| POST | `/api/ai/variant` | 变式题生成 |
| POST | `/api/ai/grade` | AI 批改 |
| POST | `/api/ocr` | 图片 OCR（PaddleOCR-VL） |
| GET | `/api/analysis/overview` | 看板统计（总量 / 学科分布 / 趋势） |
| GET | `/api/analysis/similar?content=` | 向量相似题召回 |
| GET | `/api/export/pdf` | ReportLab 生成 PDF 报告 |
| GET | `/api/export/markdown` | 导出 Markdown 复习清单 |
| GET | `/api/conversations` | 历史对话列表 |
| POST | `/api/conversations` | 新建会话 |
| GET | `/api/conversations/{cid}/messages` | 会话消息 |
| POST | `/api/test-connection` | 测试 AI 连接 |
| POST | `/api/chat` | AI 答疑（非流式） |
| POST | `/api/chat/stream` | AI 答疑（流式） |

---

## 数据与备份

本项目把**代码**与**用户数据**分离：

- **纳入 Git（本仓库）**：源码、配置样例（`.env.example`）、文档。
- **不纳入 Git**（见 `.gitignore`）：`.venv/`、`node_modules/`、`.env`（真实密钥）、`recall.db`、`chroma_data/`、`uploads/`。
- **本地用户数据备份建议**：定期复制 `backend/recall.db` 与 `backend/chroma_data/` 目录到云盘 / 移动硬盘；数据库为单文件 SQLite，直接拷贝即可。

> ⚠️ 切勿把包含 `api_key` 的 `.env` 提交到公开仓库。

---

## 项目文档

仓库内附带产品与研发文档（Markdown）：

- `PRD_Recall_v2.md` — 产品需求文档（MoSCoW / 成功指标）
- `PRD_Recall.md` / `PRD_UIUX.md` — 早期 PRD 与 UI/UX 提炼
- `DEV_PLAN.md` — 开发规划
- `TEST_REPORT.md` — 系统测试报告（20 项问题）
- `FIX_REPORT.md` — 问题修复与自测报告

---

## 目录结构

```
recall-app/
├── frontend/                  # Vue 3 + TS + Vite + Tailwind
│   ├── index.html
│   ├── vite.config.ts         # /api 代理 → localhost:8000
│   ├── tailwind.config.js     # Design System Token 映射
│   └── src/
│       ├── main.ts / App.vue  # 顶栏 + 路由 + 移动端底部 Tab
│       ├── router.ts          # 错题集 / AI答疑 / 数据看板 / 帮助
│       ├── store.ts           # 轻量全局状态
│       ├── api.ts             # mock / 后端双模式 API 封装
│       ├── mock.ts            # 演示数据
│       ├── types.ts
│       ├── components/        # TopNav / StatusBadge / MistakeCard / EntryModal / ChatWindow
│       └── views/             # MistakeBookView / AiChatView / DashboardView / HelpView
└── backend/                   # FastAPI
    ├── requirements.txt
    ├── .env.example
    └── app/
        ├── main.py            # 入口 + CORS + 路由挂载
        ├── config.py          # 环境变量集中配置
        ├── database.py        # SQLite (SQLAlchemy)
        ├── models.py          # Category / Mistake / Conversation / ChatMessage
        ├── schemas.py         # Pydantic
        ├── seed.py            # 首次启动演示数据
        ├── routers/
        │   ├── mistakes.py    # 错题/分类 CRUD + 搜索 + 分页 + SM-2 复习
        │   ├── chat.py        # 会话 + 答疑（流式）+ 连接测试
        │   └── ai.py          # analyze / variant / grade / OCR / 统计 / 相似题 / PDF / Markdown
        └── services/
            ├── ai_service.py      # 多供应商大模型（含 base_url、无 Key 降级、流式）
            ├── ocr_service.py     # PaddleOCR-VL（未安装自动降级）
            ├── vector_service.py  # ChromaDB 相似题召回
            └── review_service.py  # SM-2 遗忘曲线
```

---

## 后续路线

- 用户登录与多端同步（JWT + 云端数据库）
- 知识图谱看板（统计 + 相似题聚类可视化）
- 复习计划前端「复习」页完整接入与提醒
- 移动端 PWA / 小程序

---

## 许可证

[MIT](LICENSE) © Recall
