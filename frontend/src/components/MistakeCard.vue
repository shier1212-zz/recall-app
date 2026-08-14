<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Mistake, AiProvider } from '../types'
import { store } from '../store'
import { formatAiAnalysis } from '../utils/formatAi'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{ mistake: Mistake }>()
const showAns = ref(false)
/** 单独跟踪"重跑中"状态，让按钮能 disable 并显示进度。 */
const reparseRunning = ref(false)

const providerLabel = (p?: string) =>
  p === 'deepseek' ? 'DeepSeek'
  : p === 'zhipu' ? '智谱 GLM-4'
  : p === 'siliconflow' ? '硅基流动'
  : p === 'mock' ? '本地规则' : ''

const statusBadge = computed(() => {
  const s = props.mistake.aiStatus
  if (s === 'ok') return { txt: `✓ ${providerLabel(props.mistake.provider)} 解析`, cls: 'text-success' }
  if (s === 'partial') return { txt: `⚠ ${providerLabel(props.mistake.provider)} 部分解析（已清洗）`, cls: 'text-warning' }
  // fallback / 未知
  return { txt: '⚠ 已降级解析', cls: 'text-muted' }
})

/** 历史脏数据/双重 JSON/替代符等异常 → 经 formatAiAnalysis 规范化为可读纯文本 */
const formattedAi = computed(() => formatAiAnalysis(props.mistake.aiAnalysis))

/** 是否显示"重跑"按钮：仅当这条是降级解析或没真模型跑过时显示，避免误点浪费配额。 */
const showReparseBtn = computed(() => {
  const m = props.mistake
  return !m.provider || m.provider === 'mock' || m.aiStatus === 'fallback'
})

/** 单条重跑：用 store 当前真实配置的 keys 调 /mistakes/{id}/reparse。 */
async function onReparse() {
  if (reparseRunning.value) return
  reparseRunning.value = true
  try {
    await store.reparseMistake(props.mistake.id)
    // toast 已在 store 内处理；自动展开解析以让用户看到新结果
    showAns.value = true
  } catch { /* toast 已提示 */ }
  finally {
    reparseRunning.value = false
  }
}
</script>

<template>
  <article
    class="bg-surface border border-line rounded-card p-4 relative hover:shadow-card transition"
    @click="showAns = !showAns"
  >
    <StatusBadge :reviewed="mistake.reviewed" />

    <span class="text-cap font-semibold text-qblue bg-cblue/10 rounded-tag px-2 py-0.5">题目</span>
    <p class="mt-3 text-body font-semibold text-qblue leading-relaxed">{{ mistake.content }}</p>

    <div class="mt-3 flex flex-wrap gap-2 items-center">
      <span class="text-cap text-body border border-dashed border-line rounded-tag px-2 py-0.5">{{ mistake.subject }}</span>
      <span
        v-for="kp in mistake.knowledgePoints" :key="kp"
        class="text-cap text-body border border-dashed border-line rounded-tag px-2 py-0.5"
      >{{ kp }}</span>
      <span class="text-cap text-muted">来源：{{ mistake.source }}</span>
    </div>

    <div v-if="showAns" class="mt-3">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-cap font-semibold text-agreen bg-agreen/10 rounded-tag px-2 py-0.5">AI 解析</span>
        <span class="text-cap" :class="statusBadge.cls">{{ statusBadge.txt }}</span>
      </div>
      <p class="mt-2 text-body text-agreen bg-agreen/5 rounded-tag px-3 py-2 leading-relaxed whitespace-pre-wrap">{{ formattedAi }}</p>
    </div>

    <div class="mt-4 flex items-center gap-2">
      <button
        class="text-cap border border-line rounded-ctrl px-2.5 py-1 text-body hover:border-qblue hover:text-qblue transition"
        @click.stop="showAns = !showAns"
      >解析</button>
      <button
        v-if="showReparseBtn"
        class="text-cap border rounded-ctrl px-2.5 py-1 text-body transition flex items-center gap-1"
        :class="reparseRunning
          ? 'border-line text-muted cursor-wait'
          : 'border-agreen/40 text-agreen hover:bg-agreen hover:text-surface'"
        :disabled="reparseRunning"
        :title="reparseRunning ? '正在用当前配置的 AI 重跑…' : '用浏览器中已配置的真实 AI Key 重新解析（优先用连接成功的客户端）'"
        @click.stop="onReparse"
      >
        <span v-if="!reparseRunning">🔄 重跑 AI 解析</span>
        <span v-else>⏳ 重跑中…</span>
      </button>
      <button
        class="text-cap border border-line rounded-ctrl px-2.5 py-1 text-body hover:border-qblue hover:text-qblue transition"
        @click.stop="store.showToast('编辑功能（MVP 占位）')"
      >编辑</button>
      <button
        class="text-cap border border-line rounded-ctrl px-2.5 py-1 text-body hover:border-danger hover:text-danger transition"
        @click.stop="store.removeMistake(mistake.id)"
      >删除</button>
      <span class="ml-auto text-cap text-muted">复习 {{ mistake.reviewCount }} 次</span>
    </div>
  </article>
</template>
