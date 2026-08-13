# Recall AI 智能错题本 · UI/UX 设计基线（v0.1 草稿）

> 状态：⚠️ 草稿（由已实现前端代码反向提炼；非正式设计稿）
> 用途：作为《开发规划文档》的第二输入基线；正式设计稿产出后以正式稿为准
> 提炼来源：`frontend/src`（`App.vue` / `TopNav.vue` / `style.css` / `router.ts` / 各组件 / `tailwind.config`）
> 日期：2026-08-13

---

## 1. 信息架构

```
Recall·AI 错题本
├─ 错题集 (/)        ← 首页：列表 + 筛选 + 录入入口
├─ AI 答疑 (/ai)     ← 流式对话 + 图片识题 + 转错题
├─ 数据看板 (/dashboard) ← 趋势 + 知识图谱
├─ 帮助 (/help)      ← FAQ + 故障排查
└─ 一键复习 (/review) ← 逐题作答 + 批改
```

全局入口：桌面端顶栏导航；移动端底部 Tab（中置悬浮「＋录入」）。

---

## 2. 设计原则

1. **清晰优先**：题目(蓝)与解析(绿)强对比，一眼区分"问题"与"答案"。
2. **轻量毛玻璃**：顶栏 `glass` 半透明 + 模糊，内容区白卡浮于浅灰底。
3. **状态可见**：所有 AI/异步操作有 loading/结果/toast 反馈，杜绝白屏。
4. **本地感**：无登录墙，打开即用；设置（Key）本地保存。

---

## 3. 设计令牌（Design Tokens）

### 3.1 色彩
| Token | 值 | 用途 |
|-------|----|------|
| `--ink` | #1D1D1F | 主标题/重点文 |
| `--body` | #6E6E73 | 正文 |
| `--muted` | #AEAEB2 | 次要/占位 |
| `--q-blue` | #3B82F6 | 题目、主操作、激活态 |
| `--a-green` | #10B981 | 解析、正确/掌握 |
| `--success` | #34C759 | 成功 |
| `--warning` | #FF9500 | 部分解析/警示 |
| `--danger` | #FF3B30 | 错误/删除 |
| `--line` | #E5E5EA | 边框/分割线 |
| `--surface` | #FFFFFF | 卡片底 |
| `--bg` | #F5F5F7 | 页面底 |

**分类色板**：c-blue #3B82F6 / c-green #10B981 / c-orange #FF9500 / c-purple #AF52DE / c-pink #FF2D55 / c-cyan #64D2FF / c-amber #FFCC00 / c-indigo #5E5CE6

### 3.2 间距 / 圆角
- 间距：xs4 / sm8 / md12 / lg16 / xl24 / x2-32
- 圆角：tag 6 / ctrl 8 / card 12

### 3.3 字体
- 栈：`font-sans`（系统字体）；正文 `text-body(约15px)`，小字 `text-cap(约12px)`
- 标题用 `font-bold` + `--ink`；题目用 `font-semibold` + `--q-blue`

---

## 4. 关键界面与组件规范

### 4.1 顶栏 `TopNav`
- `sticky top-0`，高 56px，`glass` 背景，底部 `border-line`
- 左：Logo「Recall·AI 错题本」(`text-qblue`)
- 右（≥lg）：导航链接（错题集/AI/看板/帮助），激活态 `text-qblue + bg-cblue/10`

### 4.2 首页 `MistakeBookView`
- 主内容 `max-w-[1180px]` 居中
- 顶部：搜索框 + 学科/知识点/来源筛选 + 「＋录入」按钮
- 列表：`MistakeCard` 网格/单列；每张卡含 题目(蓝)、学科/知识点标签(虚线 border)、来源、复习次数、解析折叠区(绿底)、操作(解析/编辑/删除)

### 4.3 录入弹窗 `EntryModal`
- 单例（全局 `store.entryOpen`）
- 四种入口：文本粘贴 / 截图(OCR) / 图片上传 / 从对话转
- 提交时 `store.addMistake` → 自动选可用 provider + fallback

### 4.4 错题卡 `MistakeCard` + `StatusBadge`
- 解析状态徽章三态：
  - `✓ XX 解析`（`ok`，绿）
  - `⚠ XX 部分解析（原文已保留）`（`partial`，橙）
  - `⚠ 已降级`（`fallback`，橙/红）
- 解析文本 `whitespace-pre-wrap` 保留模型换行

### 4.5 AI 答疑 `ChatWindow`
- 流式渲染回答（逐字）
- 输入框左侧「📷 图片识题」：文件选择 + Ctrl+V 粘贴 → OCR → 填充输入框
- 消息可「加入错题本」

### 4.6 设置 `ApiKeyModal`
- 每个供应商：API Key 输入 + **Base URL 输入**（placeholder 默认官方地址）+「🧪 测试连接」按钮（三态：⏳测试中 / ✓XXms / ✗原因）
- 「恢复默认」清空 Base URL；保存同时存 Key 与 URL 到 localStorage

### 4.7 全局反馈
- `toast`：底部居中，深色底白字，自动消失（约 2.5s）
- 视图切换 `fade` 150ms

---

## 5. 响应式规范

| 断点 | 布局 |
|------|------|
| ≥1280 (lg) | 顶栏导航 + 居中宽内容 |
| 768–1279 | 同上，间距收紧 |
| <768 | 顶栏隐藏导航 → 底部 Tab（60px），中置悬浮「＋录入」(圆形 44px，蓝，阴影) |

- 长文解析、表格在移动端可横向滚动或折叠
- 弹窗在移动端全屏化，避免遮挡

---

## 6. 可访问性（基础）
- 语义化按钮/链接；图标配文字标签
- 颜色对比满足 WCAG AA（文 #1D1D1F on #FFF）
- 交互元素最小点击区 ≥ 44px（移动端）

---

## 7. 待正式设计补齐项
- 高保真视觉稿（Figma）与切图
- 空状态插画、加载骨架屏、动效规范
- 深色模式（当前仅浅色令牌）
- 知识图谱可视化交互细节
- 导出 PDF/Markdown 的版式规范
