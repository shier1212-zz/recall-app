<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import type { ReviewResult } from '../types'
import { formatAiAnalysis } from '../utils/formatAi'

const router = useRouter()
const showAnalysis = ref(false)

const queue = computed(() => store.reviewQueue)
const total = computed(() => queue.value.length)
const done = computed(() => store.reviewDone)
const current = computed(() => (done.value || total.value === 0 ? null : queue.value[store.reviewIndex]))
const progress = computed(() => (total.value === 0 ? 0 : Math.round((store.reviewIndex / total.value) * 100)))
const stats = computed(() => store.reviewStats)

/** 历史脏数据/双重 JSON/替代符等异常 → 经 formatAiAnalysis 规范化为可读纯文本 */
const formattedAnalysis = computed(() => (current.value ? formatAiAnalysis(current.value.aiAnalysis) : ''))

async function act(result: ReviewResult) {
  if (!current.value) return
  const ok = await store.recordReview(current.value.id, result)
  if (!ok) return
  showAnalysis.value = false
  store.advanceReview()
}

function askExit() {
  if (total.value > 0 && !done.value) {
    if (!confirm('退出后本次复习进度不保存，确定要退出吗？')) return
  }
  store.exitReview()
  router.push('/')
}

function restartUnmastered() {
  store.restartUnmasteredRound()
}
</script>

<template>
  <div class="max-w-[820px] mx-auto">
    <!-- 顶部：退出 / 进度 / 占位 -->
    <div class="flex items-center justify-between mb-5">
      <button class="text-cap text-body hover:text-ink transition flex items-center gap-1" @click="askExit">
        <span>←</span><span>退出复习</span>
      </button>
      <div v-if="!done && total > 0" class="text-cap text-body">
        第 <span class="text-ink font-semibold text-body">{{ store.reviewIndex + 1 }}</span> / {{ total }} 题
      </div>
      <div v-else-if="done" class="text-cap text-body">已完成本次复习</div>
      <div v-else class="text-cap text-body">无未复习题目</div>
      <div class="w-16"></div>
    </div>

    <!-- 进度条 -->
    <div v-if="!done && total > 0" class="h-1.5 bg-bg rounded-full overflow-hidden mb-8">
      <div class="h-full bg-cgreen transition-all duration-300" :style="{ width: progress + '%' }"></div>
    </div>

    <!-- 题目卡片（逐题模式） -->
    <div v-if="!done && current" class="bg-surface border border-line rounded-card p-6 lg:p-8 mb-6 shadow-card">
      <div class="flex items-center gap-2 mb-3 flex-wrap">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-cap bg-qblue/10 text-qblue font-semibold">
          {{ current.subject || '未分类' }}
        </span>
        <span v-if="current.reviewCount > 0" class="text-cap text-muted">
          已复习 {{ current.reviewCount }} 次
        </span>
        <span v-if="current.source" class="text-cap text-muted">
          · 来源：{{ current.source }}
        </span>
      </div>

      <h2 class="text-h2 font-semibold mb-4" style="line-height: 1.6">
        {{ current.content }}
      </h2>

      <div v-if="current.knowledgePoints && current.knowledgePoints.length" class="flex flex-wrap gap-1.5 mb-5">
        <span
          v-for="k in current.knowledgePoints" :key="k"
          class="text-cap px-2 py-0.5 border border-line rounded-ctrl text-muted"
        >
          # {{ k }}
        </span>
      </div>

      <!-- AI 解析（折叠） -->
      <div class="border-t border-line pt-4">
        <button
          class="flex items-center justify-between w-full text-cap text-body hover:text-ink transition"
          @click="showAnalysis = !showAnalysis"
        >
          <span class="flex items-center gap-1.5">
            <span class="text-cgreen">✦</span>
            <span class="font-semibold">AI 解析</span>
          </span>
          <span class="text-muted">{{ showAnalysis ? '收起 ▴' : '展开 ▾' }}</span>
        </button>
        <div
          v-if="showAnalysis"
          class="mt-3 p-3 bg-cgreen/5 border border-cgreen/30 rounded-ctrl text-body"
          style="color: #065F46; line-height: 1.7"
        >
          {{ formattedAnalysis || '暂无 AI 解析。' }}
        </div>
      </div>
    </div>

    <!-- 操作按钮（仅题目态显示） -->
    <div v-if="!done && current" class="grid grid-cols-3 gap-3">
      <button
        class="border border-warning bg-surface rounded-card py-3 text-warning font-semibold hover:bg-warning/10 transition flex flex-col items-center gap-1"
        @click="act('unmastered')"
      >
        <span class="text-xl">😅</span><span class="text-body">还不太会</span>
      </button>
      <button
        class="border border-line bg-surface text-body rounded-card py-3 font-semibold hover:border-ink hover:text-ink transition flex flex-col items-center gap-1"
        @click="act('skip')"
      >
        <span class="text-xl">⏭️</span><span class="text-body">跳过</span>
      </button>
      <button
        class="bg-success text-white rounded-card py-3 font-semibold hover:opacity-90 transition flex flex-col items-center gap-1 shadow-card"
        @click="act('mastered')"
      >
        <span class="text-xl">✅</span><span class="text-body">我已掌握</span>
      </button>
    </div>

    <!-- 结算页 -->
    <div v-if="done" class="bg-surface border border-line rounded-card p-8 text-center shadow-card">
      <div class="text-5xl mb-3">🎉</div>
      <h2 class="text-h2 font-semibold mb-2">已完成本次复习</h2>
      <p class="text-body text-muted mb-6">本次共复习 {{ total }} 道错题</p>
      <div class="grid grid-cols-3 gap-3 max-w-[480px] mx-auto mb-6">
        <div class="border border-line rounded-card py-4">
          <div class="text-h2 text-success font-bold">{{ stats.mastered }}</div>
          <div class="text-cap text-muted mt-1">已掌握</div>
        </div>
        <div class="border border-line rounded-card py-4">
          <div class="text-h2 text-warning font-bold">{{ stats.unmastered }}</div>
          <div class="text-cap text-muted mt-1">还不太会</div>
        </div>
        <div class="border border-line rounded-card py-4">
          <div class="text-h2 text-muted font-bold">{{ stats.skipped }}</div>
          <div class="text-cap text-muted mt-1">跳过</div>
        </div>
      </div>
      <div class="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          v-if="stats.unmastered > 0"
          class="border border-qblue text-qblue rounded-ctrl px-5 py-2.5 text-body font-semibold hover:bg-qblue/5 transition"
          @click="restartUnmastered"
        >再来一轮未掌握（{{ stats.unmastered }}）</button>
        <button
          class="bg-qblue text-white rounded-ctrl px-5 py-2.5 text-body font-semibold hover:opacity-90 transition"
          @click="askExit"
        >回到错题本</button>
      </div>
    </div>

    <!-- 队列为空（没题可复习） -->
    <div v-if="!done && total === 0" class="text-center py-20">
      <div class="text-5xl mb-3">🎯</div>
      <h2 class="text-h2 font-semibold mb-2">暂无未复习题目</h2>
      <p class="text-body text-muted mb-6">所有错题都已复习，继续保持！</p>
      <button
        class="bg-qblue text-white rounded-ctrl px-5 py-2.5 text-body font-semibold hover:opacity-90 transition"
        @click="askExit"
      >回到错题本</button>
    </div>
  </div>
</template>
