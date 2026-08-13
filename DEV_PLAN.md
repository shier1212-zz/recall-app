# Recall AI 智能错题本 · 开发规划文档（DEV PLAN）

> 版本：v1.0
> 编制：AI 技术负责人 / 产品经理
> 最后更新：2026-08-13
> 输入文档：
> 1. `PRD_Recall.md`（产品需求文档）
> 2. `PRD_UIUX.md`（UI/UX 设计基线——工作区原本无独立 UI/UX 文档，由已实现前端代码反向提炼为草稿，作为本规划第二输入；§0 为其摘要）

---

## 0. UI/UX 设计基线（合成自已实现前端）

> 说明：工作区未提供独立 UI/UX 文档。以下从 `frontend/src` 实际代码（`App.vue` / `TopNav.vue` / `style.css` / `router.ts` / 各组件）提炼，作为开发规划的第二输入基线。后续若产出正式 UI/UX 稿，以正式稿为准。

### 0.1 信息架构（路由）

| 路由 | 视图 | 角色 |
|------|------|------|
| `/` | `MistakeBookView` | 错题集（首页、列表+筛选+录入入口） |
| `/review` | `ReviewView` | 一键复习（逐题作答） |
| `/ai` | `AiChatView` | AI 答疑（流式对话+转错题） |
| `/dashboard` | `DashboardView` | 数据看板 |
| `/help` | `HelpView` | 帮助中心 |
| `/:pathMatch(.*)*` | NotFound | 兜底（防白屏） |

### 0.2 设计令牌（Design Tokens，来自 `style.css` + `tailwind.config`）

- **色彩语义**：`--q-blue:#3B82F6`（题目/主操作蓝）、`--a-green:#10B981`（解析/绿）、`--success:#34C759`、`--warning:#FF9500`、`--danger:#FF3B30`、`--ink:#1D1D1F`（主文）、`--body:#6E6E73`、`--muted:#AEAEB2`、`--line:#E5E5EA`、`--surface:#FFF`、`--bg:#F5F5F7`
- **分类色板**：c-blue / c-green / c-orange / c-purple / c-pink / c-cyan / c-amber / c-indigo
- **间距**：xs4 / sm8 / md12 / lg16 / xl24 / x2-32（px）
- **圆角**：`--r-tag:6` / `--r-ctrl:8` / `--r-card:12`
- **字体**：`font-sans`（系统字体栈），正文 `text-body`，小字 `text-cap`

### 0.3 组件清单

- 布局：`TopNav`（毛玻璃 sticky 顶栏）、`App`（主框架 + 移动端底 Tab + 全局 toast）
- 业务组件：`EntryModal`（录入弹窗）、`MistakeCard`（错题卡 + 解析状态徽章）、`StatusBadge`（掌握状态）、`ChatWindow`（对话窗 + 📷识题）、`ApiKeyModal`（Key/Base URL 设置 + 测试连接）
- 核心模块：`store.ts`（响应式全局态）、`api.ts`（HTTP + snake→camel 拦截）、`types.ts`、`router.ts`、`mock.ts`（USE_MOCK 模式）

### 0.4 交互规范

- 顶栏 `glass` 毛玻璃 + `sticky top-0`；主内容 `max-w-[1180px]` 居中
- 移动端（`<lg`）：隐藏顶栏导航，改用固定底部 Tab（高 60px），中置悬浮「＋录入」按钮（圆形、阴影）
- 全局 `EntryModal` 单例；操作反馈统一 `toast`（底部居中，自动消失）
- 视图切换 `fade` 过渡（150ms）
- 解析状态三态语义：`✓ 解析(ok)` / `⚠ 部分解析(partial，保留原文)` / `⚠ 已降级(fallback)`

---

## 1. 开发总纲

### 1.1 目标

在已落地的 MVP 原型（录入→解析→错题本→逐题复习→AI 对话→看板→帮助→PDF 导出）基础上，补齐 **SM-2 自动排程、OCR 真实识别、变体题/批改接入复习流、Markdown 导出、知识图谱可视化、移动端打磨、性能与测试**，达到 PRD 中 P0 全绿、P1 滚动补齐的发布标准。

### 1.2 开发原则

1. **本地优先**：错题存本地 SQLite，API Key 仅存浏览器 localStorage，随请求临时传参，后端不落库。
2. **容错优先**：任何单一 AI 供应商故障不得中断主流程（自动 fallback）；AI 返回非规范 JSON 时保留原文（`partial`），完全无响应才降级（`fallback`）。
3. **契约稳定**：前后端以 REST + JSON 为契约，字段 snake_case（后端）/ camelCase（前端），由 `api.ts` 拦截器转换；新增字段向后兼容。
4. **可观测**：所有 AI 调用在后端打 stderr 日志（`[ai_service] ...`），前端 toast 透出可读失败原因。

### 1.3 范围

- **In Scope（MVP→GA）**：§3 全部模块的功能完善、性能达标、P0/P1 验收。
- **Out of Scope（本期不做）**：多用户/云端账号体系、协作分享、完整组卷系统、移动原生 App（仅响应式 Web）。

### 1.4 当前进度快照（如实记录，避免规划脱节）

| 能力 | 状态 | 备注 |
|------|------|------|
| 文本/对话录入 + AI 解析 | ✅ 已落地 | 多供应商路由 + fallback 已验证 |
| 图片/OCR 录入 | 🟡 接口已通，依赖缺失 | `ocr_service` 缺 PaddleOCR，需装依赖或换方案 |
| 错题本 CRUD + 筛选 | ✅ 已落地 | 分类、搜索、掌握切换可用 |
| 逐题复习 | 🟡 部分 | 仅逐题标记（mastered/unmastered/skip），**无 SM-2 排程队列/到期日** |
| AI 对话（流式） | ✅ 已落地 | 流式渲染 + 转错题可用 |
| 数据看板 | ✅ 视图已落地 | 趋势/知识图谱可视化待增强 |
| 帮助中心 | ✅ 已落地 | 占位式 |
| PDF 导出 | ✅ 已落地 | ReportLab 中文 PDF |
| 变体题 / 批改 | 🟡 接口已通，未接入复习流 | `/ai/variant`、`/ai/grade` 存在，复习流未调用 |
| 相似题召回 | 🟡 接口已通，前端未用 | `/analysis/similar` + ChromaDB upsert 已接 |
| Markdown 导出 | ❌ 未做 | PRD P1 |
| 测试覆盖 | ❌ 薄弱 | 需补单测/集成/E2E |

---

## 2. 里程碑与任务分解

> 采用 2 周一个 Sprint，建议 7 个 Sprint（约 14 周）到 GA。带 ⭐ 为 P0 必交付。

### M1 · 基础巩固与可观测性（Sprint 1–2）
- [ ] ⭐ 补齐端到端冒烟测试（录入→解析→复习→对话），固化 CI 流程
- [ ] ⭐ AI fallback/partial 全链路日志与前端 toast 文案统一（接 §0.4 三态）
- [ ] ⭐ 后端 `/api/health` 增加 AI/DB/OCR 子健康探测
- [ ] 统一错误响应体 `{code, message, detail}`，前端错误拦截器改造
- [ ] `USE_MOCK` 模式文档化（联调/演示用）

### M2 · 录入闭环增强（Sprint 2–3）
- [ ] ⭐ OCR 真实落地：安装 PaddleOCR-VL 或接入云端 OCR，端到端 < 10s
- [ ] ⭐ 多题拆分：单图多题 AI 拆分为独立卡片 + 勾选导入
- [ ] ⭐ 录入结果强一致：AI 解析失败时仍保证错题入库（partial/fallback 不阻断）
- [ ] 录入表单校验与防重复（内容相似度去重，调用 `/analysis/similar`）

### M3 · 复习引擎（Sprint 3–5）⭐ 关键路径
- [ ] ⭐ 引入 `ReviewLog` 模型，落地 SM-2 算法（ease/interval/due）
- [ ] ⭐ 复习计划生成：每日/周度/考前队列（基于 due 日期聚合）
- [ ] ⭐ 复习流接入 AI 变体题（`/ai/variant`）+ 自动批改（`/ai/grade`）
- [ ] ⭐ 复习结算报告（正确率、薄弱知识点）
- [ ] 复习提醒（前端本地通知，可选）

### M4 · 看板与导出（Sprint 5–6）
- [ ] ⭐ 看板图表落地（录入/复习/正确率趋势，ECharts 或 Chart.js）
- [ ] ⭐ 知识图谱可视化（学科—知识点掌握度热力，基于 ChromaDB/统计）
- [ ] ⭐ PDF 导出增强（含解析、按分类/学科筛选导出）
- [ ] Markdown 导出（`/export/markdown` 或前端生成）
- [ ] 相似题在前端「相关错题」入口展示

### M5 · 移动端与体验打磨（Sprint 6–7）
- [ ] ⭐ 移动端（<768）核心流程验收：录入/复习/对话可用
- [ ] 响应式断点回归（表格/弹窗/长文解析排版）
- [ ] 空状态、加载态、错误态统一
- [ ] 帮助中心内容补全（FAQ + 故障排查 + Key 配置引导）

### M6 · 性能与质量（Sprint 7）
- [ ] ⭐ 性能压测：首屏 < 2s、API P95 < 500ms、AI 首字 < 2s（10,000+ 错题）
- [ ] ⭐ 列表虚拟化（长列表滚动流畅）
- [ ] 安全审计：Key 不落库校验、CORS 收敛（当前 `allow_origins=["*"]` 需按环境收紧）
- [ ] 单元测试覆盖率 ≥ 60%，关键 AI 路由集成测试

### M7 · 发布准备（Sprint 7 末）
- [ ] 打包与一键启动（`start.bat`/`stop.bat` 校验）
- [ ] 用户文档 + 隐私说明
- [ ] GA 验收（§7）

---

## 3. 组件 / 模块依赖树

### 3.1 前端依赖树

```
App.vue
├─ TopNav.vue                 (导航：错题集/AI/看板/帮助)
├─ router-view
│   ├─ MistakeBookView.vue ──► MistakeCard.vue, StatusBadge.vue, EntryModal.vue(录入)
│   ├─ ReviewView.vue      ──► (调用 /api/mistakes, /review, /ai/variant, /ai/grade)
│   ├─ AiChatView.vue      ──► ChatWindow.vue(📷识题), ApiKeyModal.vue
│   ├─ DashboardView.vue   ──► (调用 /analysis/overview, /analysis/similar)
│   └─ HelpView.vue
├─ EntryModal.vue          ──► store.addMistake → api.createMistake
├─ ApiKeyModal.vue         ──► store.save(), api.testConnection
└─ store.ts ◄── api.ts ◄── (snake→camel 拦截) ──► 后端 REST
       └─ types.ts (类型契约)
```

### 3.2 后端依赖树

```
main.py (FastAPI)
├─ middleware: CORSMiddleware
├─ routers (prefix=/api)
│   ├─ mistakes.py ──► services: ai_service, vector_service
│   │               └─ models: Mistake, Category
│   ├─ chat.py     ──► services: ai_service
│   │               └─ models: Conversation, ChatMessage
│   └─ ai.py       ──► services: ai_service, ocr_service, vector_service
│                   └─ models: Mistake, Category
├─ services
│   ├─ ai_service.py     (多供应商路由: deepseek/zhipu/siliconflow/mock + fallback + _safe_json_loads)
│   ├─ ocr_service.py    (PaddleOCR-VL，待装依赖)
│   └─ vector_service.py (ChromaDB upsert/search)
├─ models.py (SQLAlchemy)
├─ schemas.py (Pydantic: 请求/响应契约)
├─ database.py (SQLite engine + Session)
└─ seed.py (启动种子数据)
```

### 3.3 关键数据流依赖（录入→复习）

```
EntryModal → store.addMistake → api.createMistake(POST /api/mistakes)
  → ai_service.analyze_mistake(多供应商+fallback) → Mistake 入库
  → BackgroundTasks: vector_service.upsert_mistake(ChromaDB)
ReviewView → GET /api/mistakes(筛选) → POST /api/mistakes/{id}/review(result)
  → [M3 新增] ReviewLog + SM-2 排程 → GET /api/review-plan(到期队列)
  → /ai/variant(变体) → 作答 → /ai/grade(批改)
```

---

## 4. API 契约

> 基址 `http://localhost:8000/api`，前缀已含。字段后端 snake_case，前端 camelCase（拦截器转换）。

### 4.1 错题与分类

| Method | Path | 请求 | 响应 | 说明 |
|--------|------|------|------|------|
| GET | `/categories` | — | `CategoryOut[]` | 分类列表（含 count） |
| POST | `/categories` | `CategoryCreate{name,color}` | `CategoryOut` | 新建分类 |
| GET | `/mistakes` | `?category_id&q&reviewed=true\|false` | `MistakeOut[]` | 列表/搜索/筛选 |
| POST | `/mistakes` | `MistakeCreate`（见下） | `MistakeOut` | 录入 + 触发 AI 解析 |
| PATCH | `/mistakes/{mid}/toggle-review` | — | `MistakeOut` | 切换掌握态 |
| POST | `/mistakes/{mid}/review` | `ReviewRequest{result:mastered\|unmastered\|skip}` | `MistakeOut` | 逐题复习动作 |
| DELETE | `/mistakes/{mid}` | — | `{ok:true}` | 删除（同步删向量） |

**MistakeCreate**（关键字段）
```json
{
  "content": "题目文本",
  "subject": "", "knowledge_points": [], "source": "", "category_id": 1,
  "provider": "", "api_key": null, "base_url": null,
  "try_fallback": true, "preferred_providers": [],
  "all_api_keys": {}, "all_base_urls": {}
}
```
**MistakeOut**（含 AI 状态）
```json
{ "id":1, "category_id":1, "content":"", "subject":"数学",
  "knowledge_points":["导数"], "source":"", "review_count":0,
  "reviewed":false, "ai_analysis":"", "created_at":"2026-08-13T...",
  "ai_status":"ok|partial|fallback", "provider":"siliconflow" }
```

### 4.2 对话与连接测试

| Method | Path | 请求 | 响应 | 说明 |
|--------|------|------|------|------|
| GET | `/conversations` | — | `ConversationDetail[]` | 含 messages |
| POST | `/conversations` | `{title?}` | `ConversationOut` | 新建会话 |
| GET | `/conversations/{cid}/messages` | — | `MessageOut[]` | 消息列表 |
| POST | `/test-connection` | `{provider, api_key?, base_url?}` | `{ok,reason,model,latency_ms}` | 连接校验 |
| POST | `/chat` | `ChatRequest{message,conversation_id?,provider,api_key?,base_url?}` | `MessageOut` | 答疑（流式由前端 SSE/逐字实现） |

### 4.3 AI / OCR / 分析 / 导出

| Method | Path | 请求 | 响应 | 说明 |
|--------|------|------|------|------|
| POST | `/ai/analyze` | `{content}` | 解析结果 | 学科/知识点/错因/解析 |
| POST | `/ai/variant` | `{content}` | `{variant}` | 变体题 |
| POST | `/ai/grade` | `{question,answer}` | `{grade}` | 批改 |
| POST | `/ocr` | `file`(multipart) | `{text,subject}` | 图片识别 |
| GET | `/analysis/overview` | — | `{total,reviewed,todo,categories}` | 统计 |
| GET | `/analysis/similar` | `?content&k=3` | `{items}` | 相似题召回 |
| GET | `/export/pdf` | — | `application/pdf` | PDF 报告 |

### 4.4 健康与错误约定

- `GET /api/health` → `{status:"ok",service:"recall-api"}`
- 错误响应建议统一为 `{code:int, message:str, detail:str}`（M1 改造）；现有端点多用 HTTP 状态码 + `detail`。

---

## 5. 开发规范

### 5.1 前端（Vue 3 + TS + Tailwind）
- 组件用 `<script setup lang="ts">`；类型全部收敛到 `types.ts`，禁止 `any` 裸用（AI 兜底处 `as` 显式标注）。
- 样式仅用 `style.css` / `tailwind.config` 中已定义的设计令牌（颜色/圆角/间距），禁止硬编码新色值。
- 全局状态走 `store.ts`（reactive 单例），组件 props/emits 明确类型；跨组件通信经 store 或 router。
- HTTP 经 `api.ts` 统一封装，**禁止**在组件内直接 `fetch/axios`；snake→camel 转换在拦截器完成。
- 每个视图必须有空/加载/错误三态；AI 长任务显示 loading，禁止白屏。

### 5.2 后端（FastAPI + SQLAlchemy）
- 路由按 `routers/` 分域（mistakes/chat/ai），`prefix=/api`；新增能力先加 schema 再接路由。
- Pydantic 模型 `from_attributes=True`；请求模型与响应模型分离（如 `MistakeCreate`/`MistakeOut`）。
- AI 调用统一走 `ai_service`，**禁止**在路由内直接调 OpenAI SDK；多供应商逻辑封装在 `analyze_mistake`/`chat_reply` 内。
- AI 容错铁律：① 收到响应先 `_safe_json_loads`；② 解析失败保留原文 `partial`；③ 无响应 `fallback`；④ 单供应商异常不抛出中断，由 fallback 链吸收；⑤ 所有异常 `print("[ai_service] ...")` 入日志。
- 向量写用 `BackgroundTasks`，不阻塞主响应；`vector_service` 异常只告警不影响主流程。
- 密钥：`api_key`/`base_url` 仅本次请求使用，**严禁**写入数据库或日志。

### 5.3 工程与协作
- 分支：`main`（保护）/ `feature/*`（短生命周期）/ `hotfix/*`；PR 需过 CI（lint + 测试）。
- Commit 遵循 Conventional Commits（`feat:`/`fix:`/`refactor:`/`docs:`/`test:`）。
- AI 相关改动必须附「真 key 不可得时的降级验证」（如 fake key 全 fallback 正常入库）。
- 文档：接口变更同步更新本规划 §4；UI 变更同步 §0 基线。

### 5.4 测试规范
- 单测：AI 服务 `_safe_json_loads` / `analyze_mistake` fallback / SM-2 计算。
- 集成：录入→解析→复习 端到端（mock provider）。
- E2E（可选 Playwright）：录入、复习、对话三条主流程不白屏。

---

## 6. 风险矩阵

| # | 风险 | 类别 | 可能性 | 影响 | 缓解措施 |
|---|------|------|--------|------|----------|
| R1 | 第三方 LLM 不稳定（DeepSeek 过载/硅基流动小模型 JSON 不规范） | 技术 | 高 | 高 | 多供应商 fallback + `_safe_json_loads` + partial 保留原文（已落地）；P1 模型白名单 |
| R2 | OCR 依赖未装（PaddleOCR-VL）导致图片录入不可用 | 技术 | 高 | 中 | M2 装依赖或换轻量 OCR/云端 OCR；缺依赖时降级手动录入（已设计） |
| R3 | SM-2 排程缺失，复习无计划 | 产品 | 中 | 高 | M3 引入 ReviewLog + SM-2，优先于变体题 |
| R4 | CORS `allow_origins=["*"]` 生产暴露 | 安全 | 中 | 中 | M6 按环境收紧为具体前端源 |
| R5 | API Key 误落库/日志泄露 | 安全 | 低 | 高 | 代码审查 + 密钥仅 localStorage；M6 安全审计 |
| R6 | 10,000+ 错题下列表卡顿 | 性能 | 中 | 中 | M6 列表虚拟化 + 索引 |
| R7 | AI 流式首字 > 2s（网络/模型） | 性能 | 中 | 中 | 缓存常用解析；降级本地规则；超时熔断 |
| R8 | 移动端底 Tab 与大弹窗冲突 | 体验 | 中 | 低 | M5 响应式回归 + 弹窗全屏化 |
| R9 | ChromaDB 首次启动下模型阻塞 API | 技术 | 中 | 中 | 已用 BackgroundTasks 异步（保持）；加启动预热 |

---

## 7. 验收标准

### 7.1 功能验收（对标 PRD P0）
- [ ] 四种录入（拍照/截图/文本/对话）可用；OCR 端到端 < 10s（R2 闭环）
- [ ] 录入后 AI 自动返回 学科/知识点/错因/解析，三态徽章正确
- [ ] 单供应商故障自动 fallback，录入不中断、不白屏
- [ ] 错题列表可筛选/搜索/删除；分类可用
- [ ] 复习：SM-2 生成到期队列；逐题作答 + 变体题 + AI 批改 + 结算报告
- [ ] AI 对话流式首字 < 2s；可一键转错题
- [ ] 每供应商测试连接返回可读原因 + 延迟
- [ ] 看板趋势/知识图谱渲染；PDF + Markdown 导出可打开
- [ ] 帮助中心内容完整、可检索

### 7.2 非功能验收（对标 PRD §6）
- [ ] 首屏 < 2s；API P95 < 500ms；AI 首字 < 2s；OCR < 10s
- [ ] 10,000+ 错题下列表滚动流畅（虚拟化）
- [ ] 桌面/平板/移动主流浏览器可用
- [ ] 单 AI 故障主流程不中断；OCR 失败降级手动录入

### 7.3 质量门槛
- [ ] 关键链路 E2E 冒烟 100% 通过
- [ ] 单测覆盖率 ≥ 60%
- [ ] 无未捕获异常导致白屏
- [ ] 安全审计通过（Key 不落库、CORS 收敛）

---

## 8. 开发节奏建议

### 8.1 迭代模型
- **节奏**：2 周 Sprint，固定「规划→开发→演示→回顾」。
- **并行策略**：前端（UI/交互）与后端（服务/算法）按契约并行；契约（§4）在 Sprint 首日前冻结。
- **每日**：15min 异步站会（阻塞同步）；**每周**：一次跨端联调（前端 + 后端 + 真 Key 验证）。

### 8.2 人力配置（建议）
- 前端 1（Vue3/Tailwind）、后端 1（FastAPI/AI 集成）、算法/数据 0.5（SM-2/向量）、产品/测试 0.5（PRD/验收）。

### 8.3 时间线（甘特式）

```
Sprint:  1     2     3     4     5     6     7
M1 基础  ████
M2 录入        ████
M3 复习        ██████████
M4 看板              ██████
M5 移动端                  ██████
M6 性能/质                   ██████
M7 发布                          ██
```

### 8.4 节奏要点
- **M3 为关键路径**：SM-2 与复习流决定产品核心价值，优先排期、最早联调。
- **真 Key 联调日**：每个 Sprint 末固定半天，用真实 DeepSeek/智谱/硅基流动 Key 验证 fallback 与流式，避免「测试通但真分析挂」（历史已发生）。
- **契约优先**：任何接口变更先改 `schemas.py` + 本规划 §4，再动实现，减少前后端返工。
- **演示驱动**：每个 Sprint 末必须有可运行 demo（本地 `start.bat` 一键起），而非仅单测通过。

---

> 附录：本规划与 `PRD_Recall.md` 配套使用；§0 UI/UX 基线为代码反向提炼，正式 UI/UX 稿产出后以此覆盖。所有「已落地/缺失」判定截至 2026-08-13 代码快照。
