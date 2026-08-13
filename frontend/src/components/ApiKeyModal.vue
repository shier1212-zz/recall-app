<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { store } from '../store'
import * as api from '../api'
import type { AiProvider, ApiKeys, BaseUrls } from '../types'

const formKeys = reactive<ApiKeys>({ deepseek: '', zhipu: '', siliconflow: '' })
const formUrls = reactive<BaseUrls>({ deepseek: '', zhipu: '', siliconflow: '' })

watch(() => store.apiKeysOpen, (open) => {
  if (open) {
    formKeys.deepseek = store.apiKeys.deepseek ?? ''
    formKeys.zhipu = store.apiKeys.zhipu ?? ''
    formKeys.siliconflow = store.apiKeys.siliconflow ?? ''
    formUrls.deepseek = store.baseUrls.deepseek ?? ''
    formUrls.zhipu = store.baseUrls.zhipu ?? ''
    formUrls.siliconflow = store.baseUrls.siliconflow ?? ''
  }
}, { immediate: true })

// 测试状态：{ provider: { state: 'idle'|'testing'|'ok'|'fail', reason?: string, latencyMs?: number } }
type State = 'idle' | 'testing' | 'ok' | 'fail'
interface TestState { state: State; reason?: string; latencyMs?: number; model?: string }
const testStates = reactive<Record<AiProvider, TestState | undefined>>({} as any)

function setState(p: AiProvider, s: TestState | undefined) {
  if (s === undefined) delete testStates[p]
  else testStates[p] = s
}

type Pk = 'deepseek' | 'zhipu' | 'siliconflow'
const fields: { key: Pk; provider: AiProvider; label: string; url: string; hint: string; emoji: string; defaultBase: string }[] = [
  { key: 'deepseek',    provider: 'deepseek',    label: 'DeepSeek',   url: 'https://platform.deepseek.com', hint: '注册送额度', emoji: '🤖', defaultBase: 'https://api.deepseek.com/v1' },
  { key: 'zhipu',       provider: 'zhipu',       label: '智谱 GLM-4', url: 'https://open.bigmodel.cn',      hint: 'glm-4-flash 免费额度（需注册 Key）', emoji: '⚡', defaultBase: 'https://open.bigmodel.cn/api/paas/v4/' },
  { key: 'siliconflow', provider: 'siliconflow', label: '硅基流动',   url: 'https://cloud.siliconflow.cn',   hint: '注册送额度', emoji: '🌊', defaultBase: 'https://api.siliconflow.cn/v1' }
]

async function onTest(p: AiProvider) {
  // 取表单里当前未保存的 key + base_url；若为空就用 store 里已存的（场景：用户改完还没点保存）
  const k = (formKeys as any)[p as Pk] as string
  const b = (formUrls as any)[p as Pk] as string
  const apiKey = (k ?? '').trim() || store.apiKeys[p] || ''
  const baseUrl = (b ?? '').trim() || store.baseUrls[p] || ''
  setState(p, { state: 'testing' })
  try {
    const r = await api.testConnection(p, apiKey || undefined, baseUrl || undefined)
    if (r.ok) {
      setState(p, { state: 'ok', reason: r.reason, latencyMs: r.latencyMs, model: r.model })
      store.markProviderPassed(p)  // ← 关键：把通过的 provider 记到 store
      store.showToast(`✓ ${providerLabel(p)} 连通成功（${r.latencyMs} ms，模型 ${r.model}）`)
    } else {
      setState(p, { state: 'fail', reason: r.reason })
      store.markProviderFailed(p)  // ← 关键：记失败，下次自动绕开
      store.showToast(`✗ ${providerLabel(p)} 连通失败：${r.reason}`)
    }
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '未知错误'
    setState(p, { state: 'fail', reason: detail })
    store.markProviderFailed(p)
    store.showToast(`✗ ${providerLabel(p)} 测试接口异常：${detail}`)
  }
}

function providerLabel(p: AiProvider) {
  return p === 'deepseek' ? 'DeepSeek' : p === 'zhipu' ? '智谱 GLM-4' : p === 'siliconflow' ? '硅基流动' : '本地规则'
}

function save() {
  // 把表单值合并回 store（空字符串表示用户主动清空，让 store 删除该字段）
  const nextKeys: ApiKeys = { ...store.apiKeys }
  const nextUrls: BaseUrls = { ...store.baseUrls }
  for (const f of fields) {
    const k = (formKeys as any)[f.key] as string
    const u = (formUrls as any)[f.key] as string
    const trimmedK = (k ?? '').trim()
    const trimmedU = (u ?? '').trim()
    if (trimmedK) nextKeys[f.key] = trimmedK
    else delete (nextKeys as any)[f.key]
    if (trimmedU) nextUrls[f.key] = trimmedU
    else delete (nextUrls as any)[f.key]
  }
  // 即使 key 为空也要单独存一份 base_url（场景：用户用环境变量 key 但改了中转站 base）
  store.apiKeys = nextKeys
  localStorage.setItem('recall_api_keys', JSON.stringify(nextKeys))
  store.baseUrls = nextUrls
  localStorage.setItem('recall_base_urls', JSON.stringify(nextUrls))
  store.showToast('已保存（密钥 + base_url，仅存本地浏览器）')
  store.closeApiKeys()
}

function stateBadge(s?: TestState) {
  if (!s || s.state === 'idle') return { txt: '', cls: '' }
  if (s.state === 'testing') return { txt: '⏳ 测试中…', cls: 'text-muted' }
  if (s.state === 'ok') return { txt: `✓ ${s.latencyMs} ms`, cls: 'text-success' }
  return { txt: '✗ 失败', cls: 'text-danger' }
}
</script>

<template>
  <div class="fixed inset-0 z-[70] bg-ink/40 flex items-center justify-center p-4" @click.self="store.closeApiKeys()">
    <div class="w-full max-w-[600px] bg-surface rounded-card p-8 relative max-h-[90vh] overflow-y-auto">
      <button class="absolute top-4 right-4 text-muted hover:text-ink text-lg" @click="store.closeApiKeys()">✕</button>
      <h2 class="text-h2">API 密钥 / Base URL 设置</h2>
      <p class="text-cap text-body mt-1 mb-6">
        填入对应平台的密钥与 base_url 后，AI 答疑将调用该渠道的大模型。<br />
        两者都仅保存在本浏览器（localStorage），随请求临时传给后端，不写入数据库。<br />
        <span class="text-muted">点 <b>🧪 测试连接</b> 立刻校验当前表单里的 Key + base_url 是否连通。</span>
      </p>

      <div v-for="f in fields" :key="f.key" class="mb-6 pb-5 border-b border-line last:border-b-0">
        <label class="flex items-center justify-between text-body font-semibold">
          <span>{{ f.emoji }} {{ f.label }}</span>
          <span class="flex items-center gap-2">
            <span v-if="!testStates[f.provider]" class="text-cap font-normal" :class="store.apiKeys[f.key] ? 'text-success' : 'text-muted'">
              {{ store.apiKeys[f.key] ? '✓ 已配置' : '未配置' }}
            </span>
            <span v-else class="text-cap font-normal" :class="stateBadge(testStates[f.provider]).cls">
              {{ stateBadge(testStates[f.provider]).txt }}
            </span>
          </span>
        </label>
        <!-- API Key 行 -->
        <div class="flex gap-2 mt-1">
          <input
            v-model="formKeys[f.key]"
            type="password"
            :placeholder="`sk-... 在 ${f.url} 获取（${f.hint}）`"
            class="flex-1 border border-line rounded-ctrl px-3 py-2 text-body focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20"
          />
          <button
            type="button"
            class="flex items-center gap-1 border border-line rounded-ctrl px-3 py-2 text-body whitespace-nowrap hover:border-qblue hover:text-qblue transition disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="testStates[f.provider]?.state === 'testing'"
            :title="`使用当前输入框（未保存也立即生效）的 Key + base_url 测试 ${f.label} 是否连通`"
            @click="onTest(f.provider)"
          >
            <span v-if="testStates[f.provider]?.state === 'testing'" class="inline-block w-3 h-3 border-2 border-qblue border-t-transparent rounded-full animate-spin"></span>
            <span v-else>🧪</span>
            <span>{{ testStates[f.provider]?.state === 'testing' ? '测试中' : '测试连接' }}</span>
          </button>
        </div>
        <!-- Base URL 行 -->
        <div class="mt-2">
          <div class="flex items-center gap-2">
            <label class="text-cap text-muted whitespace-nowrap w-[68px] text-right">Base URL</label>
            <input
              v-model="formUrls[f.key]"
              type="text"
              :placeholder="f.defaultBase"
              class="flex-1 border border-line rounded-ctrl px-3 py-1.5 text-body font-mono focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20"
            />
            <button
              type="button"
              class="text-cap border border-line rounded-ctrl px-2 py-1 text-muted hover:border-qblue hover:text-qblue transition whitespace-nowrap"
              :title="`恢复默认 base_url: ${f.defaultBase}`"
              @click="formUrls[f.key] = ''"
            >恢复默认</button>
          </div>
          <p class="mt-1 ml-[76px] text-cap text-muted">
            留空使用默认（如 <span class="font-mono">{{ f.defaultBase }}</span>）。如有自部署中转站或反向代理，改为对应地址。
          </p>
        </div>
        <div v-if="testStates[f.provider]?.state === 'fail' && testStates[f.provider]?.reason" class="mt-2 text-cap text-danger break-words">
          {{ testStates[f.provider]?.reason }}
        </div>
        <div v-else-if="testStates[f.provider]?.state === 'ok'" class="mt-2 text-cap text-success">
          {{ testStates[f.provider]?.reason }} ·
          模型：{{ testStates[f.provider]?.model }} ·
          延迟：{{ testStates[f.provider]?.latencyMs }} ms
        </div>
      </div>

      <div class="flex justify-end gap-2 mt-8">
        <button class="border border-line rounded-ctrl px-4 py-2 text-body hover:border-qblue transition" @click="store.closeApiKeys()">取消</button>
        <button class="bg-qblue text-white rounded-ctrl px-4 py-2 text-body hover:opacity-90 transition" @click="save">保存</button>
      </div>
    </div>
  </div>
</template>
