# Recall AI 智能错题本 · 系统测试报告

> 测试角色：资深软件测试工程师（SDET）
> 测试对象：`recall-app`（Vue3 + FastAPI + SQLite + ChromaDB）
> 测试时间：2026-08-13
> 环境：前端 `VITE_USE_MOCK=false`（真实后端联调），后端 `:8000`、前端 `:5173` 均在跑
> 依据：`PRD_Recall_v2.md`、`DEV_PLAN.md`、当前代码实现

---

## 一、测试结果总览

| 维度 | 结论 | 说明 |
|------|------|------|
| 1. 功能是否符合需求 | ⚠️ 部分符合 | 核心 CRUD/复习/答疑可用；拍照录入、SM-2、流式、Markdown 导出、真实看板未达标 |
| 2. 页面交互是否正常 | ⚠️ 基本正常 | 录入「对话」tab、拍照/截图 tab 存在交互断点；其余交互流畅 |
| 3. 页面布局与响应式 | ✅ 基本合理 | 桌面/移动断点清晰，底部 Tab 设计合理；聊天页移动端高度存在遮挡风险 |
| 4. 异常情况处理 | ✅ 较稳健 | 空数据/无 Key/无效 Key/非法参数均有兜底，不白屏、不崩 |
| 5. AI 功能输出 | ⚠️ 容错好、能力弱 | 降级与容错链路优秀；但 OCR 依赖缺失、无流式、SM-2 缺失 |

**统计**：严重 1 · 一般 10 · 优化 9 · 通过项 8

---

## 二、通过项（PASS，值得保留）

1. **读取类接口稳定**：`GET /mistakes`、`/categories`、`/conversations` 正常返回（实测 28 条错题、4 分类、含 messages）。
2. **复习接口边界正确**：`mastered`→`reviewed=true,count=1`；非法 `result` 返回 `400`；不存在的题返回 `404`。
3. **无 Key 时优雅降级**：`chat(deepseek,无key)` 返回「（DeepSeek 暂未配置 API Key，已降级为规则回复）…」；`录题(mock)` 返回规则解析，**不崩溃**。
4. **test-connection 准确**：假 Key 返回 `{"ok":false,"reason":"Key 无效或已过期…","latency_ms":295}`，原因透出准确。
5. **空状态兜底齐全**：无错题（📭）、无会话（onMounted 自动建）、复习队列空（🎯）均有 UI，无白屏。
6. **路由兜底**：`/:pathMatch(.*)*` 指向 NotFound，避免空白页。
7. **XSS 安全**：题目/解析均用 Vue 文本插值 `{{ }}`，自动转义。
8. **响应式断点合理**：卡片 `grid-cols-1 md:2 xl:3`；桌面顶栏 + 移动底栏（中置「＋」突出）设计到位。

---

## 三、发现的问题（按严重程度）

### 🔴 严重（1）

**F1 · 拍照 / 截图录入主流程中断**
- 位置：`frontend/src/components/EntryModal.vue` `onFile()`
- 现象：OCR 端点返回结果后仅 `text.value = res.text`，**未切换到「文本」tab**，用户停留在上传按钮页，看不到识别出的题目，也无法提交「AI 识别并归档」。
- 实测：`POST /api/ocr` 当前返回 `{"text":"（未安装 paddleocr，OCR 不可用…）","subject":""}`——PaddleOCR 依赖根本未安装，拍照/截图两条录入方式实际不可用。
- 影响：PRD 四大录入方式占其二，且结果不可见，用户无法走通该流程。
- 备注：即使 OCR 装好，不切 tab 也会导致识别文本藏在「文本」tab 的隐藏 textarea 里，仍需手动切换，属 UX 断点。

---

### 🟡 一般（10）

**F2 · 新建错题本不持久化（前端漏调 API）**
- 位置：`MistakeBookView.addCat()` → 只 `store.categories.push(...)`，**未调用 `api.createCategory`**。
- 实测：后端 `POST /api/categories` 正常可用（T14 创建成功且复列仍在），但 UI 从未调用。
- 影响：用户新建的分类刷新后消失，造成"假保存"体验。

**F3 · 录入时无法选择错题本 / 分类**
- 位置：`EntryModal.submit()` 固定 `category_id: 1`。
- 影响：分类体系形同虚设，错题无法归入用户自建本，"错题本管理"功能不完整。

**F4 · 后端 `create_mistake` 缺少校验，产生脏数据**
- 位置：`backend/app/routers/mistakes.py`
- 实测：`category_id=999` → `HTTP=200`（孤儿题，无对应分类）；`content:""` → `HTTP=200`（空内容题）。
- 影响：SQLite 无外键约束，可写入孤儿/空题；列表筛选与统计失真。

**F5 · AI 答疑无流式输出**
- 位置：`ai_service.chat_reply` 为单次同步请求。
- 影响：PRD 非功能需求「AI 流式首字 < 2s」未实现；长回答期间界面无首字反馈，易误判为卡死。

**F6 · SM-2 复习引擎缺失**
- 位置：复习仅 `review_mistake` 标记 `mastered/unmastered/skip`，无间隔排程。
- 影响：PRD/帮助中心宣称的「基于 SM-2 遗忘曲线自动排程每日/周度/考前计划」未落地；当前只有"再来一轮未掌握"。

**F7 · 数据看板为写死演示，且文案与数据矛盾**
- 位置：`DashboardView.vue` 第 13 行写「当前为演示数据」，但卡片实际读 `store.mistakes`（真实）；趋势折线、知识图谱为硬编码 SVG。
- 影响：用户以为看板是演示，实际是真实计数但图表是假的；知识图谱未按 `/analysis/similar` 真实召回渲染。

**F8 · 帮助中心声称 Markdown 导出，实际无此功能**
- 位置：`HelpView.vue` FAQ：「支持一键导出 PDF…与 Markdown 错题清单」；但 `ai.py` 仅 `/export/pdf`，无 Markdown 接口/按钮。
- 影响：文档与功能不一致，用户按指引找不到 Markdown 导出。

**F9 · 录入「对话」tab 误导，无"加入错题本"动作**
- 位置：`EntryModal` 对话 tab + `sendChat()`：文案「描述你的错题，我来帮你整理并归类」，实际仅 `store.send()` 转发到 AI 答疑，**不创建错题**。
- 影响：PRD「AI对话：提问 → 流式回答 → 一键加入错题本」缺最后一步；用户以为在录题，实则只是聊天。

**F10 · 错题列表无分页**
- 位置：`fetchMistakes` 一次性返回全部。
- 影响：PRD 非功能要求「支持 10000+ 错题」；万级数据下全量渲染卡片有性能风险。

---

### 🟢 优化（9）

- **O1** 智谱 provider `tag:"免费"` 但 `needKey:true`，文案自相矛盾（`types.ts`）。
- **O2** `AiChatView` 用 `height: calc(100vh - 140px)` 固定高，移动端底部 Tab(60px) 可能遮挡输入框。
- **O3** `ChatWindow.runOcr` 用 `parentElement.querySelector('input[type=text],input:not([type])')` 聚焦，结构脆弱易失效。
- **O4** `main.py` `CORSMiddleware(allow_origins=["*"], allow_credentials=True)` 不安全，生产需收紧为白名单。
- **O5** API Key 仅存 `localStorage`，需提示用户本地存储风险。
- **O6** `HelpView`「联系反馈」为无事件 `span`，死链。
- **O7** 拍照 tab 占位「PaddleOCR-VL 识别题目文本与公式」与实际不可用矛盾，应标"依赖待装"。
- **O8** `store.send` 在无会话时静默 `return`，无 toast 反馈。
- **O9** 后端已实现 `/analysis/similar`（向量相似题）但 UI 未暴露，能力闲置。

---

## 四、问题严重程度汇总

| 编号 | 问题 | 严重程度 | 维度 |
|------|------|----------|------|
| F1 | 拍照/截图录入中断（OCR 缺失 + 不切 tab） | 严重 | 功能/交互 |
| F2 | 新建错题本不持久化 | 一般 | 数据 |
| F3 | 录入无法选分类 | 一般 | 功能 |
| F4 | 后端缺校验→孤儿/空题 | 一般 | 异常/数据 |
| F5 | 答疑无流式 | 一般 | AI/非功能 |
| F6 | SM-2 引擎缺失 | 一般 | 功能 |
| F7 | 看板写死演示+文案矛盾 | 一般 | 功能/交互 |
| F8 | 帮助称 Markdown 导出（无） | 一般 | 文档/功能 |
| F9 | 对话 tab 误导无归档 | 一般 | 交互/功能 |
| F10 | 列表无分页 | 一般 | 性能/非功能 |
| O1–O9 | 见上 | 优化 | 文案/布局/安全 |

---

## 五、修改建议（按优先级）

### P0（发布前必须）
1. **F1 拍照/截图录入**
   - `onFile` 成功后 `tab.value = 'text'`，并把识别文本填入可编辑 textarea；OCR 失败时 toast 明确提示"OCR 未启用，请直接粘贴文本"，并自动切到文本 tab。
   - 安装 `paddleocr`/`paddlepaddle`（或接视觉大模型 OCR）；在依赖缺失时前端「拍照/截图」tab 直接置灰并注明"OCR 待启用"。
2. **F4 入参校验**：`create_mistake` 校验 `content` 非空、`category_id` 必须存在（否则 `422`/默认归"未分类"）。

### P1（核心体验）
3. **F2/F3 分类闭环**：`addCat` 调 `api.createCategory` 并刷新；`EntryModal` 增加"错题本"下拉（默认"未分类"）。
4. **F6 SM-2**：在 `Mistake` 增 `ease_factor/interval/due_date` 字段，`review_mistake` 按 SM-2 更新；看板/首页展示"今日待复习"。
5. **F5 流式**：`chat` 改为 `StreamingResponse`，前端用 `fetch` + `ReadableStream` 增量渲染首字。
6. **F7 真实看板**：趋势接 `analysis/overview` 历史（需补按日聚合接口），知识图谱接 `analysis/similar` 或学科聚合。
7. **F8/F9 一致性**：删除 Help 中"Markdown 导出"或补 `/export/markdown`；对话 tab 增加"加入错题本"按钮，把 AI 小结转成 `NewMistake`。

### P2（稳健性/体验）
8. **F10 分页**：`GET /mistakes` 支持 `page/size`，前端虚拟滚动或分页加载。
9. **O4** CORS 收紧为前端域名白名单；**O5** Key 存储加警示。
10. **O1/O2/O3/O6/O7/O8/O9**：文案修正、移动端高度用 `flex` 而非固定 `calc`、focus 改为 ref、死链补事件、暴露相似题入口。

---

## 六、测试结论

当前版本**异常容错与降级链路做得扎实**（无 Key、无效 Key、空数据、无会话均不崩、不白屏），工程健壮性达标；但**与 PRD 的"核心价值差距"集中在三处：拍照/OCR 录入（F1）、SM-2 复习引擎（F6）、AI 流式（F5）**，且存在分类不持久（F2）、录入无分类（F3）、看板/帮助与真实能力不符（F7/F8）等体验与一致性缺陷。建议按 P0→P1→P2 顺序排期，优先打通拍照录入与分类闭环，再补 SM-2 与流式，使 MVP 真正对齐 PRD。
