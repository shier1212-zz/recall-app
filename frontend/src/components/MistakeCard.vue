<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Mistake, AiProvider } from '../types'
import { store } from '../store'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{ mistake: Mistake }>()
const showAns = ref(false)

const providerLabel = (p?: string) =>
  p === 'deepseek' ? 'DeepSeek'
  : p === 'zhipu' ? '智谱 GLM-4'
  : p === 'siliconflow' ? '硅基流动'
  : p === 'mock' ? '本地规则' : ''

const statusBadge = computed(() => {
  const s = props.mistake.aiStatus
  if (s === 'ok') return { txt: `✓ ${providerLabel(props.mistake.provider)} 解析`, cls: 'text-success' }
  if (s === 'partial') return { txt: `⚠ ${providerLabel(props.mistake.provider)} 部分解析（原文已保留）`, cls: 'text-warning' }
  // fallback / 未知
  return { txt: '⚠ 已降级解析', cls: 'text-muted' }
})
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
      <p class="mt-2 text-body text-agreen bg-agreen/5 rounded-tag px-3 py-2 leading-relaxed whitespace-pre-wrap">{{ mistake.aiAnalysis }}</p>
    </div>

    <div class="mt-4 flex items-center gap-2">
      <button
        class="text-cap border border-line rounded-ctrl px-2.5 py-1 text-body hover:border-qblue hover:text-qblue transition"
        @click.stop="showAns = !showAns"
      >解析</button>
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
