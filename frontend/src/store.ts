import { reactive } from 'vue'
import type { Category, Mistake, Conversation, NewMistake, AiProvider, ApiKeys, BaseUrls, ReviewResult } from './types'
import * as api from './api'

function loadApiKeys(): ApiKeys {
  try {
    const raw = localStorage.getItem('recall_api_keys')
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function loadBaseUrls(): BaseUrls {
  try {
    const raw = localStorage.getItem('recall_base_urls')
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function loadHealth(): { passed: AiProvider[]; failed: AiProvider[] } {
  try {
    const raw = localStorage.getItem('recall_provider_health')
    if (raw) {
      const obj = JSON.parse(raw)
      return {
        passed: Array.isArray(obj.passed) ? obj.passed : [],
        failed: Array.isArray(obj.failed) ? obj.failed : [],
      }
    }
  } catch {}
  return { passed: [], failed: [] }
}

function saveHealth(h: { passed: AiProvider[]; failed: AiProvider[] }) {
  try { localStorage.setItem('recall_provider_health', JSON.stringify(h)) } catch {}
}

/** 固定的 provider 选择优先级（业务偏好：DeepSeek → 智谱 → 硅基流动） */
const PROVIDER_PRIORITY: AiProvider[] = ['deepseek', 'zhipu', 'siliconflow']

/** 根据"测试连接记录 + 用户 key"，自动选最合适的一个 provider。
 *  规则：
 *   1. 优先用"上次测试通过"过的，且仍配着 key 的（按上次通过时间越新越优先）
 *   2. 否则按 PROVIDER_PRIORITY 选第一个"配了 key 且不在 failed 列表"的 provider
 *   3. 都失败则回退 mock（本地规则） */
function pickProvider(
  apiKeys: ApiKeys,
  health: { passed: AiProvider[]; failed: AiProvider[] },
): { provider: AiProvider; key: string } {
  // ① 已确认通过过的（按记录顺序，最近在前）
  for (const p of health.passed) {
    const k = (apiKeys[p] || '').trim()
    if (k) return { provider: p, key: k }
  }
  // ② 按业务优先级：有 key 且不在失败列表
  for (const p of PROVIDER_PRIORITY) {
    if (health.failed.includes(p)) continue
    const k = (apiKeys[p] || '').trim()
    if (k) return { provider: p, key: k }
  }
  // ③ mock
  return { provider: 'mock', key: '' }
}

/** 极简全局状态（等价轻量 Pinia，避免额外依赖） */
export const store = reactive({
  ready: false,
  loading: false,
  categories: [] as Category[],
  mistakes: [] as Mistake[],
  conversations: [] as Conversation[],
  activeConvId: 0,
  aiProvider: 'mock' as AiProvider,
  apiKeys: loadApiKeys() as ApiKeys,
  // 用户在前端填写的各 provider base_url（用于自部署中转站等场景）
  baseUrls: loadBaseUrls() as BaseUrls,
  // provider 连接测试历史（localStorage 持久化）
  providerHealth: loadHealth() as { passed: AiProvider[]; failed: AiProvider[] },
  apiKeysOpen: false,
  entryOpen: false,
  toastMsg: '',

  // ---- 复习会话状态 ----
  reviewQueue: [] as Mistake[],
  reviewIndex: 0,
  reviewStats: { mastered: 0, unmastered: 0, skipped: 0 },
  reviewUnmasteredIds: [] as number[],
  reviewDone: false,

  async init() {
    if (this.ready) return
    this.loading = true
    try {
      const [c, m, cs] = await Promise.all([
        api.fetchCategories(), api.fetchMistakes(), api.fetchConversations()
      ])
      this.categories = c
      this.mistakes = m
      this.conversations = cs
      if (cs.length) this.activeConvId = cs[0].id
    } catch (e) {
      console.error('store.init 失败（已降级为空状态）', e)
      this.categories = []; this.mistakes = []; this.conversations = []
    } finally {
      this.ready = true
      this.loading = false
    }
  },

  activeConv(): Conversation | null {
    return this.conversations.find(c => c.id === this.activeConvId) ?? null
  },

  openEntry() { this.entryOpen = true },
  closeEntry() { this.entryOpen = false },

  // ---- 复习会话 ----
  startReview(mistakes: Mistake[]) {
    this.reviewQueue = mistakes.map(m => ({ ...m }))
    this.reviewIndex = 0
    this.reviewStats = { mastered: 0, unmastered: 0, skipped: 0 }
    this.reviewUnmasteredIds = []
    this.reviewDone = mistakes.length === 0
  },
  async recordReview(id: number, result: ReviewResult) {
    try {
      const updated = await api.reviewMistake(id, result)
      // 同步主列表 & 当前队列项
      const idx = this.mistakes.findIndex(x => x.id === id)
      if (idx >= 0) this.mistakes[idx] = { ...this.mistakes[idx], ...updated }
      const qi = this.reviewQueue.findIndex(x => x.id === id)
      if (qi >= 0) this.reviewQueue[qi] = { ...this.reviewQueue[qi], ...updated }
    } catch (e) {
      console.error('recordReview 失败', e)
      this.showToast('记录复习结果失败，请重试')
      return false
    }
    if (result === 'mastered') this.reviewStats.mastered += 1
    else if (result === 'unmastered') {
      this.reviewStats.unmastered += 1
      if (!this.reviewUnmasteredIds.includes(id)) this.reviewUnmasteredIds.push(id)
    } else this.reviewStats.skipped += 1
    return true
  },
  advanceReview() {
    if (this.reviewIndex + 1 >= this.reviewQueue.length) {
      this.reviewDone = true
    } else {
      this.reviewIndex += 1
    }
  },
  restartUnmasteredRound() {
    const ids = new Set(this.reviewUnmasteredIds)
    const subset = this.mistakes.filter(m => ids.has(m.id))
    if (!subset.length) {
      this.showToast('没有未掌握的题，无需再来一轮')
      return
    }
    this.startReview(subset)
  },
  exitReview() {
    this.reviewQueue = []
    this.reviewIndex = 0
    this.reviewStats = { mastered: 0, unmastered: 0, skipped: 0 }
    this.reviewUnmasteredIds = []
    this.reviewDone = false
  },

  showToast(msg: string) {
    this.toastMsg = msg
    setTimeout(() => { if (this.toastMsg === msg) this.toastMsg = '' }, 1800)
  },

  addMistake(p: NewMistake) {
    // 自动选 provider：上次测试通过的 > 有 key 且不在失败列表 > mock
    const picked = pickProvider(this.apiKeys, this.providerHealth)
    const chosen: AiProvider = picked.provider
    const chosenKey = picked.key
    // 把所有非空 key + base_url 一起带上，让后端 fallback 时能直接用其他 provider
    const allKeys: Record<string, string> = {}
    for (const k of ['deepseek', 'zhipu', 'siliconflow'] as const) {
      const v = (this.apiKeys[k] || '').trim()
      if (v) allKeys[k] = v
    }
    const allUrls: Record<string, string> = {}
    for (const k of ['deepseek', 'zhipu', 'siliconflow'] as const) {
      const v = (this.baseUrls[k] || '').trim()
      if (v) allUrls[k] = v
    }
    // 已测试通过的 provider（按时间倒序），让后端优先尝试这些
    const preferred = this.providerHealth.passed.slice()
    return api.createMistake({
      ...p,
      provider: chosen,
      apiKey: chosenKey,
      baseUrl: (allUrls[chosen] || '').trim() || undefined,
      tryFallback: true,
      preferredProviders: preferred,
      allApiKeys: allKeys,
      allBaseUrls: allUrls
    })
      .then(m => {
        this.mistakes.unshift(m)
        // 根据后端实际返回的 provider 和 ai_status 决定 toast 文案 + provider 健康度
        const usedProv = (m.provider || chosen) as AiProvider
        const usedKey = allKeys[usedProv] || chosenKey
        const status = m.aiStatus || 'fallback'
        const label = usedProv === 'mock' ? '本地规则'
          : usedProv === 'deepseek' ? 'DeepSeek'
          : usedProv === 'zhipu' ? '智谱 GLM-4' : '硅基流动'
        if (status === 'ok') {
          this.showToast(`已录入并由 ${label} 解析 ✓`)
          if (usedProv !== 'mock') this.markProviderPassed(usedProv)
        } else if (status === 'partial') {
          // 模型有响应但 JSON 不合规（小模型常见）。仍算 AI 用通，但提示用户
          this.showToast(`已录入（${label} 已部分解析，原文已保留）`)
          if (usedProv !== 'mock') this.markProviderPassed(usedProv)
        } else {
          this.showToast(`已录入（${label} 解析失败，已降级）`)
          if (usedProv !== 'mock') this.markProviderFailed(usedProv)
        }
        return m
      })
      .catch(e => {
        console.error('addMistake 失败', e)
        this.showToast('录入失败：' + (e instanceof Error ? e.message : '未知错误'))
        throw e
      })
  },

  /** 标记 provider 测试通过。同一 provider 不会重复出现在列表头部。 */
  markProviderPassed(p: AiProvider) {
    this.providerHealth.passed = [p, ...this.providerHealth.passed.filter(x => x !== p)]
    this.providerHealth.failed = this.providerHealth.failed.filter(x => x !== p)
    saveHealth(this.providerHealth)
  },

  /** 标记 provider 测试失败。 */
  markProviderFailed(p: AiProvider) {
    this.providerHealth.failed = [p, ...this.providerHealth.failed.filter(x => x !== p)]
    this.providerHealth.passed = this.providerHealth.passed.filter(x => x !== p)
    saveHealth(this.providerHealth)
  },

  /** 清空连接测试历史（用户主动重置） */
  clearProviderHealth() {
    this.providerHealth = { passed: [], failed: [] }
    saveHealth(this.providerHealth)
  },

  async toggleReviewed(id: number) {
    await api.toggleReview(id)
    const m = this.mistakes.find(x => x.id === id)
    if (m) { m.reviewed = !m.reviewed; if (m.reviewed) m.reviewCount += 1 }
  },

  async removeMistake(id: number) {
    await api.deleteMistake(id)
    this.mistakes = this.mistakes.filter(x => x.id !== id)
    this.showToast('已删除该错题')
  },

  /** 录入时实时调用 AI 识别学科（轻量端点 /ai/classify-subject）。
   *  - 复用 pickProvider 选最合适的 provider
   *  - 拼齐所有 key + base_url 让后端 fallback 时能自动换 provider
   *  - 返回 {subject, knowledgePoints, provider, aiStatus, reason}，失败时 subject='未分类'
   */
  async classifySubject(content: string): Promise<{ subject: string; knowledgePoints: string[]; provider: string; aiStatus: 'ok' | 'fallback' | 'partial'; reason?: string }> {
    const picked = pickProvider(this.apiKeys, this.providerHealth)
    const allKeys: Record<string, string> = {}
    for (const k of ['deepseek', 'zhipu', 'siliconflow'] as const) {
      const v = (this.apiKeys[k] || '').trim()
      if (v) allKeys[k] = v
    }
    const allUrls: Record<string, string> = {}
    for (const k of ['deepseek', 'zhipu', 'siliconflow'] as const) {
      const v = (this.baseUrls[k] || '').trim()
      if (v) allUrls[k] = v
    }
    const preferred = this.providerHealth.passed.slice()
    try {
      const r = await api.classifySubject({
        content,
        provider: picked.provider,
        apiKey: picked.key,
        baseUrl: (allUrls[picked.provider] || '').trim() || undefined,
        tryFallback: true,
        preferredProviders: preferred,
        allApiKeys: allKeys,
        allBaseUrls: allUrls,
      })
      // 根据真实结果维护 provider 健康度
      if (r.aiStatus === 'ok' && picked.provider !== 'mock') this.markProviderPassed(picked.provider)
      else if (r.aiStatus === 'fallback' && picked.provider !== 'mock') this.markProviderFailed(picked.provider)
      return r
    } catch (e) {
      console.error('classifySubject 失败', e)
      return { subject: '未分类', knowledgePoints: [], provider: 'mock', aiStatus: 'fallback', reason: '本地调用失败' }
    }
  },

  async newConversation() {
    const c = await api.createConversation('新对话')
    this.conversations.unshift(c)
    this.activeConvId = c.id
    this.showToast('已新建对话')
  },

  setProvider(p: AiProvider) {
    if (this.aiProvider === p) return
    this.aiProvider = p
    const label = p === 'mock' ? '本地规则'
      : p === 'deepseek' ? 'DeepSeek'
      : p === 'zhipu' ? '智谱 GLM-4'
      : '硅基流动'
    this.showToast(`已切换到 ${label}`)
  },

  openApiKeys() { this.apiKeysOpen = true },
  closeApiKeys() { this.apiKeysOpen = false },

  saveApiKeys(keys: ApiKeys) {
    this.apiKeys = { ...this.apiKeys, ...keys }
    localStorage.setItem('recall_api_keys', JSON.stringify(this.apiKeys))
    this.showToast('API 密钥已保存（仅存本地浏览器）')
    this.closeApiKeys()
  },

  /** 新建错题本并落库（F2：避免仅存前端内存、刷新即丢） */
  async addCat(name: string, color: string = '#5E5CE6') {
    try {
      const c = await api.createCategory(name.trim(), color)
      this.categories.unshift(c)
      this.showToast(`已创建「${name}」错题本`)
      return c
    } catch (e) {
      console.error('addCat 失败', e)
      this.showToast('创建错题本失败：' + (e instanceof Error ? e.message : '未知错误'))
      throw e
    }
  },

  /** 单独保存 base_url（如自部署中转站）。空字符串视作"使用默认"。 */
  saveBaseUrls(urls: BaseUrls) {
    // 仅保留非空值；空字符串视作用户主动清空，删字段
    const next: BaseUrls = { ...this.baseUrls, ...urls }
    for (const k of ['deepseek', 'zhipu', 'siliconflow'] as const) {
      if (!next[k] || !String(next[k]).trim()) delete next[k]
    }
    this.baseUrls = next
    localStorage.setItem('recall_base_urls', JSON.stringify(this.baseUrls))
  },

  async send(text: string) {
    let conv = this.activeConv() ?? this.conversations[0]
    // 优化：无会话时自动新建，避免静默无响应
    if (!conv) {
      try { conv = await this.newConversation() } catch { return }
    }
    // 联调模式下，后端 GET /conversations 历史上不返 messages；conv.messages 可能 undefined。
    // 这里懒初始化兜底，再追加用户消息（保证"先看 user"，AI 失败也不丢）。
    if (!Array.isArray(conv.messages)) conv.messages = []
    const userMsg: import('./types').ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    }
    conv.messages.push(userMsg)
    // 自动选 provider：上次测试通过的 > 有 key 且不在失败列表 > mock
    const picked = pickProvider(this.apiKeys, this.providerHealth)
    const provider = picked.provider
    const apiKey = picked.key
    const baseUrl = (this.baseUrls[provider] || '').trim() || undefined
    try {
      const reply = await api.sendChat(text, conv.id, provider, apiKey, baseUrl)
      conv.messages.push(reply)
      const label = provider === 'mock' ? '本地规则'
        : provider === 'deepseek' ? 'DeepSeek'
        : provider === 'zhipu' ? '智谱 GLM-4' : '硅基流动'
      if (provider !== 'mock' && provider !== this.aiProvider) {
        this.showToast(`已自动切换到 ${label}（上次连通过的）`)
      }
    } catch (e: any) {
      // AI 调用失败：若当前 provider 在 passed 列表里，把它降级成 failed，避免下次再踩
      if (provider !== 'mock') this.markProviderFailed(provider)
      // 重新选一次 provider（可能切到下一个可用的）
      const retryPicked = pickProvider(this.apiKeys, this.providerHealth)
      if (retryPicked.provider !== provider && retryPicked.provider !== 'mock') {
        try {
          const retryBaseUrl = (this.baseUrls[retryPicked.provider] || '').trim() || undefined
          const reply = await api.sendChat(text, conv.id, retryPicked.provider, retryPicked.key, retryBaseUrl)
          conv.messages.push(reply)
          const label2 = retryPicked.provider === 'deepseek' ? 'DeepSeek'
            : retryPicked.provider === 'zhipu' ? '智谱 GLM-4' : '硅基流动'
          this.showToast(`原 provider 失败，已自动改用 ${label2} 重试 ✓`)
          return
        } catch {/* 也失败则走降级分支 */}
      }
      // AI 调用失败：推一条降级回复，让用户看到有响应；同时 toast 提示
      console.error('sendChat 失败', e)
      const detail = e?.response?.data?.detail || e?.message || '未知错误'
      conv.messages.push({
        id: Date.now() + 1,
        role: 'assistant',
        content: `（AI 调用失败：${detail}）请检查 API Key 或网络后再试。`,
        createdAt: new Date().toISOString(),
      })
      this.showToast(`AI 调用失败：${detail}`)
    }
  },

  /** 流式答疑（F5）：边收边渲染，满足 PRD 首字 < 2s。 */
  async sendStream(text: string) {
    let conv = this.activeConv() ?? this.conversations[0]
    if (!conv) {
      try { conv = await this.newConversation() } catch { return }
    }
    if (!Array.isArray(conv.messages)) conv.messages = []
    const userMsg: import('./types').ChatMessage = {
      id: Date.now(), role: 'user', content: text, createdAt: new Date().toISOString(),
    }
    conv.messages.push(userMsg)
    const assistantMsg: import('./types').ChatMessage = {
      id: Date.now() + 1, role: 'assistant', content: '', createdAt: new Date().toISOString(),
    }
    conv.messages.push(assistantMsg)

    const providerLabel = (p: AiProvider) =>
      p === 'deepseek' ? 'DeepSeek' : p === 'zhipu' ? '智谱 GLM-4' : p === 'siliconflow' ? '硅基流动' : '本地规则'

    const tryOne = async (provider: AiProvider, apiKey: string): Promise<boolean> => {
      const baseUrl = (this.baseUrls[provider] || '').trim() || undefined
      try {
        await api.sendChatStream(text, conv!.id, provider, apiKey, baseUrl, (chunk) => {
          assistantMsg.content += chunk
        })
        if (provider !== 'mock') this.markProviderPassed(provider)
        return true
      } catch (e) {
        console.error('sendChatStream 失败', e)
        return false
      }
    }

    const picked = pickProvider(this.apiKeys, this.providerHealth)
    const ok = await tryOne(picked.provider, picked.key)
    if (ok) return
    // fallback 到下一个可用 provider
    if (picked.provider !== 'mock') this.markProviderFailed(picked.provider)
    const retry = pickProvider(this.apiKeys, this.providerHealth)
    if (retry.provider !== 'mock' && retry.provider !== picked.provider) {
      const ok2 = await tryOne(retry.provider, retry.key)
      if (ok2) { this.showToast(`已改用 ${providerLabel(retry.provider)} 重试 ✓`); return }
    }
    if (!assistantMsg.content.trim()) {
      assistantMsg.content = '（AI 调用失败，请检查 API Key 或网络后再试）'
    }
  }
})