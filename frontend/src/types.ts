/** 领域类型定义 */
export interface Category {
  id: number
  name: string
  color: string
  count: number
}

export interface Mistake {
  id: number
  categoryId: number
  content: string
  subject: string
  knowledgePoints: string[]
  source: string
  reviewCount: number
  reviewed: boolean
  aiAnalysis: string
  createdAt: string
  /** 后端返回：
   *   'ok'      = 真 AI 解析成功（拿到合法 JSON）
   *   'partial' = 模型有响应但 JSON 不合法（保留原文作 ai_analysis），仍算可用
   *   'fallback'= 降级（key 失效 / 网络错误 等完全没拿到响应） */
  aiStatus?: 'ok' | 'partial' | 'fallback'
  /** 后端实际调用的 provider 名 */
  provider?: string
  // SM-2 复习排程字段
  easinessFactor?: number
  intervalDays?: number
  dueDate?: string | null
}

export interface NewMistake {
  content: string
  subject: string
  knowledgePoints: string[]
  source?: string
  categoryId?: number
  /** AI 解析用的 provider 与对应 API Key（来自 store.apiKeys）；两者由前端按优先级自动选 */
  provider?: AiProvider
  apiKey?: string
  /** 当前 provider 的 base_url（来自 store.baseUrls）；用户在前端表单可改写 */
  baseUrl?: string
  /** 后端解析失败时是否自动尝试下一个 provider（默认 true） */
  tryFallback?: boolean
  /** 前端记录的"已测试通过"的 provider 列表（按时间倒序），后端优先尝试这些 */
  preferredProviders?: AiProvider[]
  /** 把前端配置的所有 key 都带过去（{deepseek: 'sk-...', siliconflow: 'sk-...'}），
   *  让后端 fallback 时也能用上其他 provider 的 key，无需再问前端 */
  allApiKeys?: Record<string, string>
  /** 把前端配置的所有 base_url 都带过去（{deepseek: '...', zhipu: '...', siliconflow: '...'}），
   *  让后端 fallback 时按 provider 选用对应的 base_url，无需再问前端 */
  allBaseUrls?: Record<string, string>
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  provider?: AiProvider
}

export interface Conversation {
  id: number
  title: string
  messages: ChatMessage[]
}

// ---- AI 提供商选择 ----
export type AiProvider = 'mock' | 'deepseek' | 'zhipu' | 'siliconflow'

export interface ProviderInfo {
  key: AiProvider
  label: string
  emoji: string
  tag: string   // 角标文案（免Key / 免费 / API）
  needKey: boolean
}

export const AI_PROVIDERS: ProviderInfo[] = [
  { key: 'mock',        label: '本地规则',   emoji: '🧪', tag: '免Key', needKey: false },
  { key: 'deepseek',    label: 'DeepSeek',   emoji: '🤖', tag: 'API',   needKey: true  },
  { key: 'zhipu',       label: '智谱 GLM-4', emoji: '⚡', tag: '免费额度',  needKey: true  },
  { key: 'siliconflow', label: '硅基流动',   emoji: '🌊', tag: 'API',   needKey: true  }
]

/** 用户在前端填写的各平台 API 密钥（仅存 localStorage，随请求临时传给后端） */
export interface ApiKeys {
  deepseek?: string
  zhipu?: string
  siliconflow?: string
}

/** 用户在前端填写的各平台 API base_url（如自部署中转站）。
 *  空字符串表示使用后端默认 base；未填（undefined）也表示使用默认。 */
export interface BaseUrls {
  deepseek?: string
  zhipu?: string
  siliconflow?: string
}

/** 测试连接历史：哪些 provider 连通过（成功过）、哪些连通过失败。
 *  用于"多 API 客户端时，默认用上次连成功的那个"，并避开已知失败的。 */
export interface ProviderHealth {
  /** 已确认连通过的 provider 列表（按成功时间倒序，越新越靠前） */
  passed: AiProvider[]
  /** 已确认连失败的 provider 列表（同样按时间倒序） */
  failed: AiProvider[]
}

/** 一题一题复习动作的结果类型 */
export type ReviewResult = 'mastered' | 'unmastered' | 'skip'

// ==================== 答题圈（社区帖子 / 评论） ====================

export interface CommunityPost {
  id: number
  title: string
  summary: string
  subject: string
  authorName: string
  authorColor: string
  viewCount: number
  likeCount: number
  shareCount: number
  commentCount: number
  createdAt: string
  liked: boolean       // 当前设备是否已点赞
  mine: boolean        // 当前设备是否是作者
  fullText?: string    // 仅详情时有
  solution?: string    // 仅详情时有
}

export interface CommunityComment {
  id: number
  postId: number
  authorName: string
  authorColor: string
  content: string
  likeCount: number
  createdAt: string
}