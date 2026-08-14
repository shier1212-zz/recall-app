import axios from 'axios'
import type { Category, Mistake, Conversation, NewMistake, ChatMessage, AiProvider, ReviewResult } from './types'
import { mockCategories, mockMistakes, mockConversations, nextId } from './mock'

/** VITE_USE_MOCK=true（默认）→ 使用本地 mock 数据；false → 请求 FastAPI 后端 */
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

/** 把后端 snake_case 响应转成前端 camelCase，避免字段缺失触发模板 undefined 异常 */
function toCamelKeys(obj: any): any {
  if (Array.isArray(obj)) return obj.map(toCamelKeys)
  if (obj && typeof obj === 'object' && obj.constructor === Object) {
    const out: any = {}
    for (const k of Object.keys(obj)) {
      const ck = k.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
      out[ck] = toCamelKeys(obj[k])
    }
    return out
  }
  return obj
}

http.interceptors.response.use(res => {
  if (res.data && typeof res.data === 'object') res.data = toCamelKeys(res.data)
  return res
})

// ---- mock 内部状态（便于增删改演示） ----
let mistakes: Mistake[] = [...mockMistakes]
let categories: Category[] = [...mockCategories]
let conversations: Conversation[] = [...mockConversations]
let msgSeq = 10000

export async function fetchCategories(): Promise<Category[]> {
  if (USE_MOCK) return categories
  const { data } = await http.get('/categories')
  return data
}

export async function fetchMistakes(): Promise<Mistake[]> {
  if (USE_MOCK) return mistakes
  const { data } = await http.get('/mistakes')
  return data
}

/** 学习看板聚合数据（真实统计：总数/已掌握/待复习/今日到期/学科分布/近7日趋势） */
export async function fetchOverview(): Promise<{
  total: number; reviewed: number; todo: number; categories: number; due_today: number;
  subject_stats: { subject: string; count: number }[]; trend: { date: string; count: number }[];
}> {
  if (USE_MOCK) {
    const total = mistakes.length
    const reviewed = mistakes.filter(m => m.reviewed).length
    return {
      total, reviewed, todo: total - reviewed, categories: categories.length, due_today: 0,
      subject_stats: [], trend: [],
    }
  }
  const { data } = await http.get('/analysis/overview')
  return data
}

export async function fetchConversations(): Promise<Conversation[]> {
  if (USE_MOCK) return conversations
  const { data } = await http.get('/conversations')
  return data
}

export async function createMistake(p: NewMistake): Promise<Mistake> {
  if (USE_MOCK) {
    const m: Mistake = {
      id: nextId(),
      categoryId: p.categoryId ?? 1,
      content: p.content,
      subject: p.subject,
      knowledgePoints: p.knowledgePoints,
      source: p.source ?? '手动录入',
      reviewCount: 0,
      reviewed: false,
      aiAnalysis: `AI 已识别：学科 ${p.subject}，知识点 ${p.knowledgePoints.join(' / ')}，已自动归档并加入今日复习计划。`,
      createdAt: new Date().toISOString()
    }
    mistakes = [m, ...mistakes]
    const c = categories.find(x => x.id === m.categoryId)
    if (c) c.count += 1
    categories[0].count += 1
    return m
  }
  // 真实联调：把前端选的 provider + apiKey + baseUrl 透传给后端（拦截器会自动 snake_case）
  // 同时把"已测试通过的 provider 列表"和"所有 API Key + base_url"都带上，让后端能自动 fallback 到其他可用 provider
  const { data } = await http.post('/mistakes', {
    content: p.content,
    subject: p.subject,
    knowledge_points: p.knowledgePoints,
    source: p.source ?? '',
    category_id: p.categoryId ?? 1,
    provider: p.provider ?? '',
    api_key: p.apiKey ?? null,
    base_url: p.baseUrl ?? null,
    try_fallback: p.tryFallback ?? true,
    preferred_providers: p.preferredProviders ?? [],
    all_api_keys: p.allApiKeys ?? {},
    all_base_urls: p.allBaseUrls ?? {}
  })
  return data
}

export async function toggleReview(id: number): Promise<void> {
  if (USE_MOCK) {
    const m = mistakes.find(x => x.id === id)
    if (m) { m.reviewed = !m.reviewed; if (m.reviewed) m.reviewCount += 1 }
    return
  }
  await http.patch(`/mistakes/${id}/toggle-review`)
}

/** 一题一题复习：mastered=已掌握 / unmastered=还不太会（仅累加计数）/ skip=跳过（不改状态） */
export async function reviewMistake(id: number, result: ReviewResult): Promise<Mistake> {
  if (USE_MOCK) {
    const m = mistakes.find(x => x.id === id)
    if (m) {
      if (result === 'mastered') { m.reviewed = true; m.reviewCount += 1 }
      else if (result === 'unmastered') { m.reviewCount += 1 }
      // skip: no-op
    }
    return { ...(m as Mistake) }
  }
  const { data } = await http.post(`/mistakes/${id}/review`, { result })
  return data
}

export async function deleteMistake(id: number): Promise<void> {
  if (USE_MOCK) { mistakes = mistakes.filter(x => x.id !== id); return }
  await http.delete(`/mistakes/${id}`)
}

/** 错题 AI 重跑解析：把当前 store 真实配置的 keys 透传后端，强制用真模型再解析一次。
 *  返回最新的 MistakeOut（ai_status/provider/ai_analysis 会被覆盖）。 */
export async function reparseMistake(p: {
  id: number;
  provider: AiProvider;
  apiKey: string;
  baseUrl?: string;
  tryFallback?: boolean;
  preferredProviders?: AiProvider[];
  allApiKeys?: Record<string, string>;
  allBaseUrls?: Record<string, string>;
}): Promise<Mistake> {
  if (USE_MOCK) {
    // mock: 直接覆盖 aiAnalysis 模拟"重跑成功"
    const idx = mistakes.findIndex(m => m.id === p.id)
    if (idx < 0) throw new Error('错题不存在')
    const updated: Mistake = {
      ...mistakes[idx],
      aiAnalysis: `（mock 重跑）已用 ${p.provider} 重新解析：本题是 ${mistakes[idx].subject} 基础题，重点掌握 ${mistakes[idx].knowledgePoints.join(' / ')}。`,
      provider: p.provider,
      aiStatus: 'ok',
    }
    mistakes[idx] = updated
    return updated
  }
  const { data } = await http.post(`/mistakes/${p.id}/reparse`, {
    provider: p.provider,
    api_key: p.apiKey ?? null,
    base_url: p.baseUrl ?? null,
    try_fallback: p.tryFallback ?? true,
    preferred_providers: p.preferredProviders ?? [],
    all_api_keys: p.allApiKeys ?? {},
    all_base_urls: p.allBaseUrls ?? {},
  })
  return data
}

export async function createConversation(title: string): Promise<Conversation> {
  if (USE_MOCK) {
    const c: Conversation = { id: nextId() + 500, title, messages: [] }
    conversations = [c, ...conversations]
    return c
  }
  const { data } = await http.post('/conversations', { title })
  return data
}

/** 新建错题本（F2：持久化，避免刷新即丢） */
export async function createCategory(name: string, color?: string): Promise<Category> {
  if (USE_MOCK) {
    const c: Category = { id: nextId() + 900, name, color: color || '#3B82F6', count: 0 }
    categories = [c, ...categories]
    return c
  }
  const { data } = await http.post('/categories', { name, color: color || '#3B82F6' })
  return data
}

// ---------------- AI 答疑（多 provider） ----------------
function providerTag(p: AiProvider): string {
  return p === 'deepseek' ? 'DeepSeek'
    : p === 'zhipu' ? '智谱 GLM-4'
    : p === 'siliconflow' ? '硅基流动'
    : ''
}

function mockReply(text: string, provider: AiProvider): string {
  let body = ''
  if (/导数|切线|积分|函数|单调/.test(text)) body = '函数类问题：先求导 f\'(x)，代入给定点得斜率，再结合 f(x0) 求切线方程；单调性看导数符号。需要我出一道变式题巩固吗？'
  else if (/力|牛顿|物理|加速度|位移/.test(text)) body = '物理题先找合力：a=F/m，再由 v=v0+at、x=v0t+½at² 求解。可去「复习」页做专项突破。'
  else if (/语法|虚拟|时态|insist/.test(text)) body = '语法点已定位：insist/suggest 表"坚持要求/建议"时，从句用 (should)+动词原形。'
  else body = '已为你定位相关错题与知识点并归档。可切到「错题集」查看归类，或到「复习」页开始今日计划。'
  const tag = providerTag(provider)
  return tag ? `【${tag}（mock）】${body}` : body
}

export async function sendChat(message: string, conversationId?: number, provider: AiProvider = 'mock', apiKey?: string, baseUrl?: string): Promise<ChatMessage> {
  if (USE_MOCK) {
    const reply: ChatMessage = {
      id: msgSeq++,
      role: 'assistant',
      content: mockReply(message, provider),
      createdAt: new Date().toISOString(),
      provider
    }
    return reply
  }
  const { data } = await http.post('/chat', { conversation_id: conversationId, message, provider, api_key: apiKey ?? null, base_url: baseUrl ?? null })
  return data
}

export async function ocrUpload(file: File): Promise<{ text: string; subject: string }> {
  if (USE_MOCK) return { text: '（OCR mock）已识别题目占位文本，请手动补充题目内容…', subject: '数学' }
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await http.post('/ocr', fd)
  return data
}

export async function exportPdf(): Promise<{ ok: boolean }> {
  if (USE_MOCK) return { ok: true }
  const { data } = await http.get('/export/pdf', { responseType: 'blob' })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url; a.download = 'recall_report.pdf'; a.click()
  URL.revokeObjectURL(url)
  return { ok: true }
}

/** Markdown 错题清单导出（F8：补齐 PRD 要求） */
export async function exportMarkdown(): Promise<{ ok: boolean }> {
  if (USE_MOCK) return { ok: true }
  const { data } = await http.get('/export/markdown', { responseType: 'blob' })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url; a.download = 'recall_mistakes.md'; a.click()
  URL.revokeObjectURL(url)
  return { ok: true }
}

/**
 * 流式答疑（F5）：用 fetch 读取 /chat/stream 的 text/plain 分块响应。
 * onToken 每收到一段文本即回调，便于前端边收边渲染（首字 < 2s）。
 * 返回完整文本供调用方落库。
 */
export async function sendChatStream(
  message: string,
  conversationId: number | undefined,
  provider: AiProvider,
  apiKey: string | undefined,
  baseUrl: string | undefined,
  onToken: (chunk: string) => void,
): Promise<string> {
  // mock 模式：用本地规则回复，分片回调模拟流式
  if (USE_MOCK) {
    const reply = mockReply(message, provider)
    const parts = reply.match(/[\s\S]{1,4}/g) || [reply]
    for (const p of parts) {
      onToken(p)
      await new Promise(r => setTimeout(r, 12))
    }
    return reply
  }
  const body = JSON.stringify({
    conversation_id: conversationId ?? null,
    message,
    provider,
    api_key: apiKey ?? null,
    base_url: baseUrl ?? null,
  })
  const resp = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  })
  if (!resp.ok || !resp.body) {
    const txt = await resp.text().catch(() => '')
    throw new Error(txt || `HTTP ${resp.status}`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let full = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value, { stream: true })
    if (chunk) {
      full += chunk
      onToken(chunk)
    }
  }
  return full
}

/** 测试某个 provider+apiKey 是否可用。仅返回布尔+原因，不入库。 */
export async function testConnection(provider: AiProvider, apiKey?: string, baseUrl?: string): Promise<{ ok: boolean; reason: string; model: string; latencyMs: number }> {
  if (USE_MOCK) return { ok: true, reason: 'mock 模式默认连通', model: 'mock', latencyMs: 0 }
  const { data } = await http.post('/test-connection', { provider, api_key: apiKey ?? null, base_url: baseUrl ?? null })
  return data
}

/** 轻量学科分类（录入题目时实时调用）：
 *  - POST /ai/classify-subject，返回 {subject, knowledge_points, provider, ai_status}
 *  - mock 模式：用本地规则按学科关键词兜底返回学科
 *  - 前端可传入 allApiKeys/allBaseUrls 让后端 fallback 轮询其他 provider
 */
export async function classifySubject(p: {
  content: string;
  provider?: AiProvider;
  apiKey?: string;
  baseUrl?: string;
  tryFallback?: boolean;
  preferredProviders?: AiProvider[];
  allApiKeys?: Record<string, string>;
  allBaseUrls?: Record<string, string>;
}): Promise<{ subject: string; knowledgePoints: string[]; provider: string; aiStatus: 'ok' | 'fallback' | 'partial'; reason?: string }> {
  if (USE_MOCK) {
    // mock：用 ai_service 同款关键词兜底
    const c = p.content || ''
    let subject = ''
    const map: [RegExp, string][] = [
      [/导数|切线|积分|函数|单调|极值|不等式|数列/, '数学'],
      [/牛顿|加速度|位移|力|电场|磁场|光|物理/, '物理'],
      [/化学键|反应|元素|摩尔|化学/, '化学'],
      [/细胞|遗传|DNA|基因|生物/, '生物'],
      [/语法|虚拟|时态|从句|单词|英语/, '英语'],
      [/古诗|文言文|作文|语文/, '语文'],
      [/朝代|战争|革命|历史/, '历史'],
      [/哲学|经济|政治|时政/, '政治'],
      [/气候|经度|纬度|公转|自转|地理/, '地理'],
    ]
    for (const [re, sub] of map) { if (re.test(c)) { subject = sub; break } }
    return { subject: subject || '未分类', knowledgePoints: [], provider: 'mock', aiStatus: subject ? 'ok' : 'fallback' }
  }
  const { data } = await http.post('/ai/classify-subject', {
    content: p.content,
    provider: p.provider ?? '',
    api_key: p.apiKey ?? null,
    base_url: p.baseUrl ?? null,
    try_fallback: p.tryFallback ?? true,
    preferred_providers: p.preferredProviders ?? [],
    all_api_keys: p.allApiKeys ?? {},
    all_base_urls: p.allBaseUrls ?? {},
  })
  // 后端 snake_case → 已被拦截器转 camelCase
  return data
}