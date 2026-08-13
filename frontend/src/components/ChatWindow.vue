<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import type { ChatMessage, AiProvider, ProviderInfo } from '../types'
import * as api from '../api'
import { store } from '../store'

const props = defineProps<{
  messages: ChatMessage[]
  providers: ProviderInfo[]
  current: AiProvider
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
  (e: 'provider-change', p: AiProvider): void
  (e: 'open-keys'): void
}>()

const input = ref('')
const box = ref<HTMLElement | null>(null)
const fileRef = ref<HTMLInputElement | null>(null)
const recognizing = ref(false)

watch(
  () => props.messages.length,
  async () => { await nextTick(); if (box.value) box.value.scrollTop = box.value.scrollHeight }
)

function onSend() {
  const t = input.value.trim()
  if (!t) return
  emit('send', t)
  input.value = ''
}

// ---- 图片识题（选文件 / 粘贴截图） ----
function pickFile() { fileRef.value?.click() }
async function onFileChange(e: Event) {
  const t = e.target as HTMLInputElement
  const f = t.files?.[0]
  t.value = ''  // 重置，允许再次选同一文件
  if (f) await runOcr(f)
}

async function onPaste(e: ClipboardEvent) {
  if (recognizing.value) return
  const items = e.clipboardData?.items
  if (!items) return
  for (const it of Array.from(items)) {
    if (it.kind === 'file' && it.type.startsWith('image/')) {
      const f = it.getAsFile()
      if (f) { e.preventDefault(); await runOcr(f); return }
    }
  }
}

async function runOcr(file: File) {
  if (recognizing.value) return
  recognizing.value = true
  store.showToast('正在识别图片中的题目…')
  try {
    const { text } = await api.ocrUpload(file)
    const cleaned = (text || '').trim()
    if (cleaned) {
      // 把识别结果填入输入框，让用户确认后再发送（不擅自直接发）
      input.value = cleaned
      await nextTick()
      const el = (box.value?.parentElement?.querySelector('input[type=text],input:not([type])')) as HTMLInputElement | null
      el?.focus()
      store.showToast('识别完成 ✓ 请确认后发送')
    } else {
      store.showToast('未识别到文字，请重试或直接输入')
    }
  } catch (err) {
    console.error('OCR 识别失败', err)
    store.showToast('图片识别失败：' + (err instanceof Error ? err.message : '未知错误'))
  } finally {
    recognizing.value = false
  }
}

onMounted(() => window.addEventListener('paste', onPaste))
onBeforeUnmount(() => window.removeEventListener('paste', onPaste))
</script>

<template>
  <div class="flex-1 flex flex-col min-w-0 h-full">
    <!-- AI 提供商选择器 -->
    <div class="mb-3 flex flex-wrap items-center gap-2">
      <span class="text-cap text-muted mr-1">AI 提供商</span>
      <button
        v-for="p in providers" :key="p.key"
        class="flex items-center gap-1.5 text-cap border rounded-ctrl px-2.5 py-1.5 transition"
        :class="current === p.key
          ? 'bg-qblue text-white border-qblue shadow-sm'
          : 'border-line text-body hover:border-qblue hover:text-qblue'"
        @click="emit('provider-change', p.key)"
        :title="p.needKey ? '需配置对应 API Key（backend/.env）' : '无需 API Key'"
      >
        <span class="text-body">{{ p.emoji }}</span>
        <span class="font-semibold">{{ p.label }}</span>
        <span
          class="text-[10px] px-1.5 py-0.5 rounded-tag"
          :class="current === p.key ? 'bg-white/20 text-white' : 'bg-bg text-muted'"
        >{{ p.tag }}</span>
      </button>

      <button
        class="ml-auto flex items-center gap-1 text-cap border border-dashed border-line rounded-ctrl px-2.5 py-1.5 text-body hover:border-qblue hover:text-qblue transition"
        @click="emit('open-keys')"
        title="配置各 AI 平台的 API 密钥"
      >🔑 设置 Key</button>
    </div>

    <div ref="box" class="flex-1 overflow-y-auto pr-1 space-y-3">
      <div class="border border-dashed border-line rounded-card p-6 text-center text-body">
        你好，我是 Recall AI 答疑助手 🤖<br />
        在上方选择 AI 提供商，我将结合知识点为你讲解并生成变式题。
      </div>

      <div
        v-for="m in messages" :key="m.id"
        class="flex gap-2 items-start"
        :class="m.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          v-if="m.role === 'assistant'"
          class="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-white text-sm font-bold"
          style="background: linear-gradient(135deg, #3B82F6, #10B981)"
        >R</div>
        <div
          class="max-w-[78%] text-body px-3 py-2 rounded-ctrl whitespace-pre-wrap break-words"
          :class="m.role === 'user' ? 'bg-qblue text-white' : 'bg-surface border border-line text-ink'"
        >{{ m.content }}</div>
      </div>
    </div>

    <div class="flex gap-2 mt-3 pt-3 border-t border-line items-center">
      <button
        type="button"
        class="w-10 h-10 flex items-center justify-center text-xl rounded-ctrl border border-line text-body hover:border-qblue hover:text-qblue hover:bg-qblue/5 transition disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="recognizing"
        :title="recognizing ? '正在识别…' : '图片识题（支持上传或粘贴截图）'"
        @click="pickFile"
      >
        <span v-if="recognizing" class="inline-block w-4 h-4 border-2 border-qblue border-t-transparent rounded-full animate-spin"></span>
        <span v-else>📷</span>
      </button>
      <input
        ref="fileRef"
        type="file"
        accept="image/*"
        class="hidden"
        @change="onFileChange"
      />
      <input
        v-model="input"
        :disabled="recognizing"
        placeholder="输入你的问题，或粘贴截图识题…"
        class="flex-1 border border-line rounded-ctrl px-3 py-2 text-body focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20 disabled:bg-bg disabled:cursor-not-allowed"
        @keydown.enter="onSend"
      />
      <button
        class="bg-qblue text-white rounded-ctrl px-4 py-2 text-body hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="recognizing"
        @click="onSend"
      >发送</button>
    </div>
  </div>
</template>