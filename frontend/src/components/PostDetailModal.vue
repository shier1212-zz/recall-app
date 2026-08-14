<script setup lang="ts">
/**
 * 帖子详情浮窗：完整题目 → 博主解答 → 评论列表 → 评论输入。
 * 顶部带 ❌ 关闭；点赞/评论联动；转发 = 复制链接 + share_count++。
 */
import { computed, onMounted, ref, watch } from 'vue'
import {
  getCommunityPost, listCommunityComments, addCommunityComment,
  toggleCommunityLike, shareCommunityPost,
  type CommunityPost, type CommunityComment
} from '../api'
import { store } from '../store'

const props = defineProps<{ postId: number }>()
const emit = defineEmits<{ close: []; changed: [] }>()

const post = ref<CommunityPost | null>(null)
const comments = ref<CommunityComment[]>([])
const loading = ref(true)
const composerName = ref(localStorage.getItem('recall_display_name') || '我')
const composerText = ref('')
const submitting = ref(false)
const sharing = ref(false)

async function load() {
  loading.value = true
  try {
    post.value = await getCommunityPost(props.postId)
    comments.value = await listCommunityComments(props.postId)
  } catch (e) {
    store.showToast('加载帖子失败：' + (e as Error).message)
    emit('close')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.postId, load)

// 局部视图状态：点赞 loading / 闪烁反馈
const togglingLike = ref(false)
async function onLike() {
  if (!post.value || togglingLike.value) return
  togglingLike.value = true
  // 乐观更新
  const wasLiked = post.value.liked
  post.value.liked = !wasLiked
  post.value.likeCount += wasLiked ? -1 : 1
  try {
    const r = await toggleCommunityLike(props.postId)
    post.value.liked = r.liked
    post.value.likeCount = r.likeCount
    emit('changed')
  } catch (e) {
    // 回滚
    post.value.liked = wasLiked
    post.value.likeCount += wasLiked ? 1 : -1
    store.showToast('点赞失败：' + (e as Error).message)
  } finally {
    togglingLike.value = false
  }
}

async function onShare() {
  if (!post.value || sharing.value) return
  sharing.value = true
  try {
    const r = await shareCommunityPost(props.postId)
    post.value.shareCount = r.shareCount
    emit('changed')
    // 复制当前 URL 到剪贴板
    const url = location.origin + location.pathname + `#/posts/${props.postId}`
    try { await navigator.clipboard.writeText(url) } catch { /* 权限失败也无所谓 */ }
    store.showToast(`🔗 已复制链接 · 累计转发 ${r.shareCount}`)
  } catch (e) {
    store.showToast('转发失败：' + (e as Error).message)
  } finally {
    sharing.value = false
  }
}

async function onSubmitComment() {
  if (!composerText.value.trim() || submitting.value) return
  const name = composerName.value.trim() || '匿名'
  localStorage.setItem('recall_display_name', name)
  submitting.value = true
  try {
    const c = await addCommunityComment(props.postId, name, composerText.value.trim())
    comments.value = [...comments.value, c]
    if (post.value) post.value.commentCount++
    composerText.value = ''
    emit('changed')
    store.showToast('评论已发布 💬')
  } catch (e) {
    store.showToast('评论失败：' + (e as Error).message)
  } finally {
    submitting.value = false
  }
}

const initial = computed(() => (post.value?.authorName || '匿').slice(0, 1))

function relativeTime(iso: string): string {
  const t = new Date(iso).getTime()
  const diff = Date.now() - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  if (diff < 30 * 86_400_000) return `${Math.floor(diff / 86_400_000)} 天前`
  return new Date(iso).toLocaleDateString()
}
</script>

<template>
  <!-- 背景遮罩 -->
  <div
    class="fixed inset-0 z-[70] bg-ink/40 flex items-start justify-center p-4 overflow-y-auto"
    @click.self="emit('close')"
  >
    <div class="bg-surface rounded-card shadow-card max-w-[760px] w-full my-8 max-h-[calc(100vh-4rem)] overflow-hidden flex flex-col">
      <!-- 头部 -->
      <div class="flex items-start justify-between px-6 py-4 border-b border-line">
        <div class="flex items-center gap-2 min-w-0">
          <span
            v-if="post"
            class="w-9 h-9 rounded-full flex items-center justify-center text-white font-bold shrink-0"
            :style="{ background: post.authorColor }"
          >{{ initial }}</span>
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-semibold text-body">{{ post?.authorName }}</span>
              <span v-if="post?.subject" class="text-cap px-1.5 py-0.5 rounded bg-cblue/10 text-qblue">{{ post.subject }}</span>
            </div>
            <p class="text-cap text-muted mt-0.5">{{ post ? relativeTime(post.createdAt) : '' }}</p>
          </div>
        </div>
        <button
          class="text-muted hover:text-ink text-2xl leading-none px-2 shrink-0"
          aria-label="关闭"
          @click="emit('close')"
        >×</button>
      </div>

      <div v-if="loading" class="p-10 text-center text-muted">加载中…</div>

      <div v-else-if="post" class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        <!-- 标题 -->
        <h2 class="text-h2 font-bold leading-snug">{{ post.title }}</h2>

        <!-- 完整题目 -->
        <section v-if="post.fullText">
          <h3 class="text-cap text-muted uppercase tracking-wide mb-2">📝 完整题目</h3>
          <div class="bg-bg border border-line rounded-ctrl p-4 text-body whitespace-pre-wrap leading-relaxed">{{ post.fullText }}</div>
        </section>

        <!-- 博主解答 -->
        <section v-if="post.solution">
          <h3 class="text-cap text-muted uppercase tracking-wide mb-2">💡 博主答题思路</h3>
          <div
            class="bg-cgreen/5 border border-cgreen/30 rounded-ctrl p-4 text-body whitespace-pre-wrap leading-relaxed"
            style="color: #065F46"
          >{{ post.solution }}</div>
        </section>

        <!-- 阅读 / 点赞 / 分享 操作行 -->
        <div class="flex items-center gap-3 pt-2 border-t border-line">
          <button
            class="flex items-center gap-1.5 text-body px-3 py-1.5 rounded-ctrl border transition"
            :class="post.liked ? 'bg-qblue/10 text-qblue border-qblue/40' : 'border-line hover:border-qblue hover:text-qblue'"
            :disabled="togglingLike"
            @click="onLike"
          >
            <span class="text-lg leading-none">{{ post.liked ? '👍' : '👍' }}</span>
            <span>{{ post.liked ? '已点赞' : '点赞' }}</span>
            <span class="text-cap text-muted">({{ post.likeCount }})</span>
          </button>
          <button
            class="flex items-center gap-1.5 text-body px-3 py-1.5 rounded-ctrl border border-line hover:border-qblue hover:text-qblue transition"
            :disabled="sharing"
            @click="onShare"
          >
            <span>🔗</span><span>转发</span>
            <span class="text-cap text-muted">({{ post.shareCount }})</span>
          </button>
          <span class="ml-auto text-cap text-muted flex items-center gap-1">
            <span>👁</span><span>{{ post.viewCount }} 浏览</span>
          </span>
        </div>

        <!-- 评论区 -->
        <section>
          <h3 class="text-cap text-muted uppercase tracking-wide mb-3">
            💬 讨论区 <span class="ml-1 normal-case">({{ comments.length }})</span>
          </h3>

          <!-- 评论输入 -->
          <div class="border border-line rounded-ctrl p-3 mb-4 bg-bg">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-cap text-muted">昵称</span>
              <input
                v-model="composerName"
                class="flex-1 bg-transparent text-body outline-none border-b border-transparent focus:border-qblue transition"
                maxlength="20"
                placeholder="你的昵称"
              />
            </div>
            <textarea
              v-model="composerText"
              rows="2"
              maxlength="500"
              class="w-full bg-transparent text-body outline-none resize-none placeholder:text-muted/60"
              placeholder="说说你的想法、补充解法或提问…"
              @keydown.ctrl.enter="onSubmitComment"
              @keydown.meta.enter="onSubmitComment"
            />
            <div class="flex items-center justify-between mt-1">
              <span class="text-cap text-muted">{{ composerText.length }} / 500（Ctrl+Enter 发送）</span>
              <button
                class="text-cap bg-qblue text-white px-3 py-1 rounded-ctrl disabled:opacity-50 hover:opacity-90 transition"
                :disabled="!composerText.trim() || submitting"
                @click="onSubmitComment"
              >{{ submitting ? '发送中…' : '发送' }}</button>
            </div>
          </div>

          <!-- 评论列表 -->
          <div v-if="comments.length === 0" class="text-center text-muted text-cap py-6">
            还没有讨论 · 来当沙发吧 🛋
          </div>
          <ul v-else class="space-y-3">
            <li v-for="c in comments" :key="c.id" class="flex gap-3">
              <span
                class="w-8 h-8 rounded-full flex items-center justify-center text-white text-cap font-bold shrink-0"
                :style="{ background: c.authorColor }"
              >{{ (c.authorName || '匿').slice(0, 1) }}</span>
              <div class="flex-1 min-w-0">
                <div class="flex items-baseline gap-2">
                  <span class="font-semibold text-body">{{ c.authorName }}</span>
                  <span class="text-cap text-muted">{{ relativeTime(c.createdAt) }}</span>
                </div>
                <p class="text-body mt-0.5 whitespace-pre-wrap break-words leading-relaxed">{{ c.content }}</p>
              </div>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>