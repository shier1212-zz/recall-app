<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import { ocrUpload } from '../api'

const router = useRouter()
const tab = ref<'photo' | 'shot' | 'text' | 'chat'>('photo')
const text = ref('')
const subject = ref('')                 // 默认空，等待 AI 实时识别
const kps = ref('')
const source = ref('手动录入')
const msg = ref('')
const uploading = ref(false)
const classifying = ref(false)          // 学科识别 loading
const classifyReason = ref('')          // 识别失败/降级原因（用于提示）
const aiSubject = ref(false)            // 当前学科是否由 AI 给出（true → 用户没手动改过）
const categoryId = ref<number>(1)
const dragOver = ref(false)             // 截图 tab 拖拽高亮
const pasteHint = ref('')               // 截图 tab 粘贴反馈（"检测到剪贴板图片，识别中…"）

const subjects = ['数学', '物理', '英语', '化学', '生物', '历史', '政治', '地理', '语文', '信息']

const tabs = [
  { key: 'photo' as const, label: '📷 拍照' },
  { key: 'shot' as const, label: '✂️ 截图' },
  { key: 'text' as const, label: '📝 文本' },
  { key: 'chat' as const, label: '💬 对话' }
]

// 默认选中第一个错题本
watch(
  () => store.categories,
  (cats) => {
    if (cats.length && !cats.find(c => c.id === categoryId.value)) categoryId.value = cats[0].id
  },
  { immediate: true }
)

// 学科识别：录入时实时调用 AI（debounced 800ms，避免每次按键都打 API）
let classifyTimer: number | null = null
function scheduleClassify(textContent: string) {
  if (classifyTimer) window.clearTimeout(classifyTimer)
  const c = (textContent || '').trim()
  // 太短不调（< 4 个有效字符，避免噪声请求）；但只要内容变化就清掉旧值，避免残留旧学科
  if (c.length < 4) {
    classifyReason.value = c ? '题目太短，请补全后再识别' : ''
    classifying.value = false
    return
  }
  classifyTimer = window.setTimeout(async () => {
    classifying.value = true
    try {
      const r = await store.classifySubject(c)
      // 只在"AI 仍是主来源"时覆盖；用户手动选了学科后不再回写
      if (aiSubject.value) {
        if (r.subject && r.subject !== '未分类') {
          subject.value = r.subject
        }
        // 知识点也顺手回填（仅当用户没填）
        if (r.knowledgePoints && r.knowledgePoints.length && !kps.value.trim()) {
          kps.value = r.knowledgePoints.join('、')
        }
      }
      classifyReason.value = r.aiStatus === 'fallback' ? (r.reason || 'AI 识别失败，请手动选择学科') : ''
    } finally {
      classifying.value = false
    }
  }, 800)
}

// 文本 tab：题目内容变化时触发学科识别
watch(text, (v) => scheduleClassify(v))
// 对话 tab：口述内容变化时触发
watch(msg, (v) => scheduleClassify(v))

// 用户手动点击学科按钮时：标记为非 AI 来源，AI 不再覆盖
function pickSubjectManually(s: string) {
  subject.value = s
  aiSubject.value = false
  classifyReason.value = ''
}

async function submit() {
  if (!text.value.trim()) { store.showToast('请先填写题目内容'); return }
  // 若 AI 还没识别或识别失败，主动再调一次以确保学科合理
  if (!subject.value.trim() || subject.value === '未分类') {
    classifying.value = true
    try {
      const r = await store.classifySubject(text.value.trim())
      if (r.subject && r.subject !== '未分类') subject.value = r.subject
      if (r.knowledgePoints?.length && !kps.value.trim()) kps.value = r.knowledgePoints.join('、')
    } finally {
      classifying.value = false
    }
  }
  await store.addMistake({
    content: text.value.trim(),
    subject: subject.value,
    knowledgePoints: kps.value.split(/[,，\/\s]+/).filter(Boolean),
    source: source.value || '手动录入',
    categoryId: categoryId.value,
  })
  text.value = ''; kps.value = ''; subject.value = ''; aiSubject.value = false; classifyReason.value = ''
  store.closeEntry()
}

async function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (!f) return
  await processFile(f)
  input.value = ''  // 允许重复选择同一文件
}

// 共享逻辑：上传一张图片 → OCR → 切到文本 tab → 自动 AI 识别学科
async function processFile(f: File) {
  uploading.value = true
  try {
    const res = await ocrUpload(f)
    tab.value = 'text'  // F1：无论成功与否都切到文本 tab，让用户看到/补充题目
    if (res.text && res.text.trim()) {
      text.value = res.text
      // OCR 后清掉旧的学科标记，让 watch(text) → scheduleClassify → AI 重新识别
      subject.value = ''
      aiSubject.value = true
      classifyReason.value = ''
      store.showToast('OCR 识别完成，AI 正在识别学科…')
    } else {
      store.showToast('未能识别到文字，请手动输入题目')
    }
  } catch (err: any) {
    // 后端 OCR 路由已经按错误类型返回 4xx/5xx + {code, message}；
    // 拉出后端给的真实原因，避免把降级文案当识别结果塞进 textarea（之前就是这里把
    // "（未安装 paddleocr…）" 直接回填给用户，严重误导）。
    const detail = err?.response?.data?.detail
    const code = typeof detail === 'object' ? detail?.code : ''
    const msg = typeof detail === 'object'
      ? (detail?.message || err?.message || '')
      : (detail || err?.message || '')
    const friendly: Record<string, string> = {
      ocr_unavailable: 'OCR 不可用：后端依赖（paddleocr / paddlepaddle）未安装。请到 backend/ 执行 `pip install paddleocr paddlepaddle`，或直接在文本框里手动输入题目。',
      ocr_failed: 'OCR 识别失败，请换一张更清晰的图片重试，或手动输入题目。',
    }
    store.showToast(friendly[code] || `OCR 失败：${msg || '请手动输入题目'}`)
    // 关键修复：之前 catch 没清空 text，导致旧残留 / 失败文案还在 textarea 里。
    // 现在明确把文本框留空，让用户看到一个干净的手动输入区。
    tab.value = 'text'
    text.value = ''
    subject.value = ''
    aiSubject.value = false
    classifyReason.value = ''
  } finally {
    uploading.value = false
  }
}

// 拖拽截图 → processFile
function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
  dragOver.value = true
}
function handleDragLeave(e: DragEvent) {
  // mouseout 时只在离开整个容器时取消高亮，避免子元素穿越时闪烁
  if (e.currentTarget === e.target) dragOver.value = false
}
async function handleDrop(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
  const f = e.dataTransfer?.files?.[0]
  if (!f) return
  if (!f.type.startsWith('image/')) {
    store.showToast('请拖拽图片文件')
    return
  }
  await processFile(f)
}

// Ctrl+V 粘贴板截图 → processFile（全局监听：焦点不必在 modal 内）
function handlePaste(e: ClipboardEvent) {
  // 只在截图 tab 响应，避免在文本/对话 tab 误吞用户的文字粘贴
  if (tab.value !== 'shot') return
  const items = e.clipboardData?.items
  if (!items || items.length === 0) return
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      e.preventDefault()
      const f = item.getAsFile()
      if (f) {
        // 截屏工具默认文件名会是 "image.png"，重命名带时间戳，便于 OCR 端排查
        const namedFile = f.name && f.name !== 'image.png'
          ? f
          : new File([f], `paste-${Date.now()}.png`, { type: f.type })
        pasteHint.value = '已捕获剪贴板图片，正在 OCR…'
        processFile(namedFile).finally(() => { pasteHint.value = '' })
      }
      return
    }
  }
  // 剪贴板里没有图片，但用户按了 Ctrl+V，给个温和提示
  pasteHint.value = '剪贴板里没有图片（按 Ctrl+Shift+S / Win+Shift+S 截屏后再粘贴）'
  setTimeout(() => { pasteHint.value = '' }, 3500)
}

onMounted(() => {
  // document 级监听：焦点落在 modal 内任意元素（含截图 tab 容器）时，
  // Ctrl+V 都会被页面收到，paste 事件对象随后能拿到完整的 clipboardData.items
  document.addEventListener('paste', handlePaste as EventListener)
})
onBeforeUnmount(() => {
  document.removeEventListener('paste', handlePaste as EventListener)
  if (classifyTimer) window.clearTimeout(classifyTimer)
})

async function archiveFromChat() {
  if (!msg.value.trim()) { store.showToast('请先描述你的错题'); return }
  // 对话归档前再次确认学科（与 submit 同样的兜底）
  if (!subject.value.trim() || subject.value === '未分类') {
    classifying.value = true
    try {
      const r = await store.classifySubject(msg.value.trim())
      if (r.subject && r.subject !== '未分类') subject.value = r.subject
    } finally {
      classifying.value = false
    }
  }
  await store.addMistake({
    content: msg.value.trim(),
    subject: subject.value,
    knowledgePoints: kps.value.split(/[,，\/\s]+/).filter(Boolean),
    source: '对话录入',
    categoryId: categoryId.value,
  })
  msg.value = ''; subject.value = ''; aiSubject.value = false; classifyReason.value = ''
  store.closeEntry()
}

function gotoChat() {
  store.closeEntry()
  router.push('/chat')
}
</script>

<template>
  <div class="fixed inset-0 z-[70] bg-ink/40 flex items-center justify-center p-4" @click.self="store.closeEntry()">
    <div class="w-full max-w-[560px] bg-surface rounded-card p-8 relative max-h-[90vh] overflow-y-auto">
      <button class="absolute top-4 right-4 text-muted hover:text-ink text-lg" @click="store.closeEntry()">✕</button>
      <h2 class="text-h2">录入错题</h2>
      <p class="text-cap text-body mt-1">选择一种方式，AI 将自动识别学科、知识点与错因并归档。</p>

      <div class="flex gap-2 flex-wrap mt-6">
        <button
          v-for="t in tabs" :key="t.key"
          class="flex-1 min-w-[110px] border rounded-ctrl px-2 py-2.5 text-body transition"
          :class="tab === t.key ? 'border-qblue bg-cblue/10 text-qblue font-semibold' : 'border-line hover:border-qblue'"
          @click="tab = t.key"
        >{{ t.label }}</button>
      </div>

      <!-- 拍照 -->
      <div v-if="tab === 'photo'" class="mt-4 border border-line rounded-card p-6 text-center">
        <p class="text-body text-body">📷 取景框</p>
        <p class="text-cap text-muted mt-1">OCR 自动提取题目文本（若未安装识别依赖，可手动输入）</p>
        <label class="inline-block mt-4 bg-qblue text-white rounded-ctrl px-4 py-2 text-body cursor-pointer hover:opacity-90 transition">
          {{ uploading ? '识别中…' : '拍照 / 相册' }}
          <input type="file" accept="image/*" class="hidden" @change="onFile" />
        </label>
      </div>

      <!-- 截图 -->
      <div
        v-if="tab === 'shot'"
        class="mt-4 border-2 border-dashed rounded-card p-6 text-center transition"
        :class="dragOver ? 'border-qblue bg-cblue/5' : 'border-line'"
        tabindex="0"
        @dragover="handleDragOver"
        @dragleave="handleDragLeave"
        @drop="handleDrop"
      >
        <p class="text-body text-body">✂️ 拖拽截图到此处，或按 <kbd class="px-1.5 py-0.5 border border-line rounded text-cap">Ctrl</kbd> + <kbd class="px-1.5 py-0.5 border border-line rounded text-cap">V</kbd> 粘贴</p>
        <p class="text-cap text-muted mt-1">OCR 自动提取题目文本（支持截图工具、剪贴板图片）</p>
        <p v-if="pasteHint" class="text-cap text-qblue mt-2 animate-pulse">✨ {{ pasteHint }}</p>
        <label class="inline-block mt-4 border border-line rounded-ctrl px-4 py-2 text-body cursor-pointer hover:border-qblue transition">
          选择截图
          <input type="file" accept="image/*" class="hidden" @change="onFile" />
        </label>
      </div>

      <!-- 文本 -->
      <div v-if="tab === 'text'" class="mt-4">
        <textarea
          v-model="text" placeholder="粘贴或输入题目内容…"
          class="w-full border border-line rounded-ctrl p-3 text-body resize-y min-h-[96px] focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20"
        />
        <div class="flex items-center gap-2 my-3">
          <span class="text-cap text-muted whitespace-nowrap">学科</span>
          <span v-if="classifying" class="text-cap text-qblue animate-pulse">AI 识别中…</span>
          <span v-else-if="subject && aiSubject" class="text-cap text-qblue">✨ AI 已识别</span>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="s in subjects" :key="s"
            class="text-cap border border-dashed rounded-tag px-2 py-0.5 transition"
            :class="subject === s ? 'bg-qblue text-white border-qblue' : 'border-line text-body hover:border-qblue'"
            @click="pickSubjectManually(s)"
          >{{ s }}</button>
        </div>
        <p v-if="classifyReason" class="text-cap text-warn mt-2">⚠️ {{ classifyReason }}</p>
        <input
          v-model="kps" placeholder="知识点（可选，AI 识别后会自动补充）"
          class="w-full border border-line rounded-ctrl px-3 py-2 text-body mt-2 focus:outline-none focus:border-qblue"
        />
        <div class="flex items-center gap-2 mt-2">
          <label class="text-cap text-muted whitespace-nowrap">错题本</label>
          <select
            v-model.number="categoryId"
            class="flex-1 border border-line rounded-ctrl px-3 py-2 text-body bg-surface focus:outline-none focus:border-qblue"
          >
            <option v-for="c in store.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <input
          v-model="source" placeholder="来源（如：期中月考）"
          class="w-full border border-line rounded-ctrl px-3 py-2 text-body mt-2 focus:outline-none focus:border-qblue"
        />
      </div>

      <!-- 对话 -->
      <div v-if="tab === 'chat'" class="mt-4">
        <p class="text-cap text-body mb-2">口述或粘贴你的错题，AI 将自动识别学科、知识点并归档到所选错题本。</p>
        <textarea
          v-model="msg" placeholder="例如：这道导数题我不会，求 y=x² 在 x=1 处的切线方程…"
          class="w-full border border-line rounded-ctrl p-3 text-body resize-y min-h-[96px] focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20"
        />
        <div class="flex items-center gap-2 mt-3">
          <span class="text-cap text-muted whitespace-nowrap">学科</span>
          <span v-if="classifying" class="text-cap text-qblue animate-pulse">AI 识别中…</span>
          <span v-else-if="subject && aiSubject" class="text-cap text-qblue">✨ {{ subject || '待识别' }}</span>
          <span v-else-if="subject" class="text-cap text-body">{{ subject }}</span>
        </div>
        <p v-if="classifyReason" class="text-cap text-warn mt-1">⚠️ {{ classifyReason }}</p>
        <div class="flex gap-2 mt-3">
          <button class="bg-qblue text-white rounded-ctrl px-4 py-2 text-body hover:opacity-90 transition" @click="archiveFromChat">AI 识别并归档</button>
          <button class="border border-line rounded-ctrl px-4 py-2 text-body hover:border-qblue transition" @click="gotoChat">去 AI 答疑提问</button>
        </div>
        <p class="text-cap text-muted mt-2">已归档的题目可在「错题集」查看，AI 解析完成后自动加入复习计划。</p>
      </div>

      <div class="flex justify-end gap-2 mt-8">
        <button class="border border-line rounded-ctrl px-4 py-2 text-body hover:border-qblue transition" @click="store.closeEntry()">取消</button>
        <button class="bg-qblue text-white rounded-ctrl px-4 py-2 text-body hover:opacity-90 transition" @click="submit">AI 识别并归档</button>
      </div>
    </div>
  </div>
</template>