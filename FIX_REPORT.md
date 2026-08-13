# Recall 测试问题修复报告（FIX_REPORT）

> 对照 `TEST_REPORT.md` 的 20 项问题，本轮以「代码修改 + 后端接口自测」闭环修复。
> 修复日期：2026-08-13

## 一、修复概览

| 问题编号 | 严重度 | 修复状态 | 说明 |
|---------|--------|---------|------|
| F1 | 🔴 严重 | ✅ 已修复 | 拍照/截图录入主流程中断：OCR 后切文本 tab + 失败提示，结果可见 |
| F2 | 🟡 一般 | ✅ 已修复 | 新建错题本持久化（调 `POST /api/categories`，刷新不丢） |
| F3 | 🟡 一般 | ✅ 已修复 | 录入可选错题本（下拉绑定 `categoryId`） |
| F4 | 🟡 一般 | ✅ 已修复 | 后端校验 `content` 非空 + `category_id` 存在（422） |
| F5 | 🟡 一般 | ✅ 已修复 | 答疑流式输出（`/chat/stream` + 前端边收边渲染） |
| F6 | 🟡 一般 | ✅ 已修复 | SM-2 复习引擎（字段 + 排程算法 + `/review/plan`） |
| F7 | 🟡 一般 | ✅ 已修复 | 看板真实数据（overview 聚合 + 前端趋势/学科分布） |
| F8 | 🟡 一般 | ✅ 已修复 | Markdown 导出（`/export/markdown`）+ 文案对齐 |
| F9 | 🟡 一般 | ✅ 已修复 | 对话 tab 误导 → 改为「AI 识别并归档」+跳转答疑；智谱 tag 澄清 |
| F10 | 🟡 一般 | ✅ 已修复 | 列表分页（后端 limit/offset + 前端分片） |
| O-CORS | 🟢 优化 | ✅ 已修复 | CORS 收紧为明确前端来源（去 `*`+credentials 隐患） |
| O-智谱tag | 🟢 优化 | ✅ 已修复 | tag 改「免费额度」并注明需注册 Key |
| O-死链 | 🟢 优化 | ✅ 已修复 | Help「联系反馈」死链 → 跳转 AI 答疑 |
| O-无会话 | 🟢 优化 | ✅ 已修复 | `store.send` 无会话自动建会话 |
| O-移动端 | 🟢 优化 | ✅ 已修复 | 聊天页 `min-height` 下调，缓解遮挡 |

## 二、后端改动文件

- **`backend/app/models.py`**：`Mistake` 新增 SM-2 字段 `easiness_factor / interval_days / due_date`；补 `Float` import。
- **`backend/app/main.py`**：CORS 收紧为 `BACKEND_CORS_ORIGINS`（默认 `localhost:5173`/`127.0.0.1:5173`）；启动期 `migrate_columns()` 用 `ALTER TABLE` 补 SM-2 列（兼容已有库，不删数据）。
- **`backend/app/schemas.py`**：`MistakeOut` 加 `easiness_factor/interval_days/due_date`（**Optional 兼容旧 NULL 行，修复全量 500**）；`MistakeCreate` 默认即可。
- **`backend/app/routers/mistakes.py`**：
  - `create_mistake` 校验 `content` 非空、`category_id` 存在 → 422；
  - `list_mistakes` 加 `limit/offset` 分页；
  - `review_mistake` 按 SM-2 更新 `interval_days / easiness_factor / due_date`；
  - 新增 `GET /review/plan`（total/reviewed/todo/due_today）。
- **`backend/app/routers/chat.py`**：新增 `POST /chat/stream`（StreamingResponse，text/plain 分块；流式结束后独立会话落库 assistant 消息）。
- **`backend/app/services/ai_service.py`**：新增 `chat_reply_stream()` 生成器（mock/无 Key/异常一次性降级；正常逐 token 流式）。
- **`backend/app/routers/ai.py`**：`/analysis/overview` 增强返回 `subject_stats / trend(近7日) / due_today`；新增 `GET /export/markdown`。

## 三、前端改动文件

- **`types.ts`**：`Mistake` 加 `easinessFactor/intervalDays/dueDate`；智谱 `tag` 改「免费额度」。
- **`api.ts`**：加 `createCategory / exportMarkdown / sendChatStream`（含 mock 分片模拟）；`createMistake` 透传 `category_id`。
- **`store.ts`**：加 `addCat()`（持久化新建错题本）；`send` 无会话自动 `newConversation()`；加 `sendStream()`（流式发送 + provider fallback）。
- **`components/EntryModal.vue`**：F1 `onFile` 成功/失败均切文本 tab 并提示；F3 录入选错题本下拉；F9 对话 tab 改「AI 识别并归档」+「去 AI 答疑提问」。
- **`views/MistakeBookView.vue`**：F2 `addCat` 调 `store.addCat`；F10 前端分片分页 + 翻页控件。
- **`components/ApiKeyModal.vue`**：智谱 hint 澄清「免费额度（需注册 Key）」。
- **`views/HelpView.vue`**：F8 文案对齐实现；死链改为跳转 `/chat`。
- **`views/DashboardView.vue`**：F7 渲染真实趋势折线 + 学科分布条形。
- **`views/AiChatView.vue`**：F5 绑定 `store.sendStream`；移动端高度优化。
- **`components/ChatWindow.vue`**：已 `emit('send')`，由 `sendStream` 驱动流式渲染。

## 四、自测结果（curl 直连真实后端）

```
✅ F4 入参校验
   POST /mistakes content=" "        → HTTP 422（题目内容不能为空）
   POST /mistakes category_id=999     → HTTP 422（错题本不存在）
✅ F6 SM-2 复习算法
   mastered×1 → reviewed=True interval=1 ef=2.6 due=次日
   mastered×2 → reviewed=True interval=6 ef=2.7（间隔按 SM-2 延长）
   unmastered → reviewed=False interval=1 ef=2.5（重置）
   非法 result="xxx"                  → HTTP 400
✅ F5 流式答疑
   POST /chat/stream provider=mock    → HTTP 200 text/plain 逐段返回降级文本
✅ F7 看板真实数据
   GET /analysis/overview
     total=35 reviewed=3 todo=32 due_today=0
     subject_stats=[数学30,化学2,英语1,物理1,地理1]
     trend=近7日（今日35，前6日0）
✅ F8 Markdown 导出
   GET /export/markdown              → HTTP 200 text/markdown 10993B（含按学科分组+解析）
✅ F2 分类持久化
   POST /categories name=自测错题本  → 再次出现于 GET /categories（刷新不丢）
✅ 回归：/mistakes 全量 HTTP 200（修复原 500：旧行 easiness_factor=NULL 触发 Pydantic 校验失败）
```

## 五、遗留与待验证

1. **前端需硬刷新**：本次改了 `store/types/api` 等模块，vite HMR 已生效但建议浏览器 `Ctrl+Shift+R` 强制刷新一次。
2. **OCR 真实识别**：本机未安装 PaddleOCR 依赖，`/api/ocr` 仍返回降级提示。F1 已确保「识别失败不中断、结果可见、可手动输入」。安装 `paddleocr` 后即全自动。
3. **移动端真机**：聊天页高度已优化，建议真机再验输入区不被遮挡。
4. **测试数据**：自测创建的题目保留在测试库中（不影响功能），如需纯净可清空 `backend/recall.db` 后重启。
