<script setup lang="ts">
/**
 * 答题圈：社区帖子列表（CSDN 风格）。
 * 顶部右侧「+ 发布题目」入口。
 * 点击帖子卡片 → 弹出 PostDetailModal。
 */
import { onMounted, ref } from 'vue'
import {
  listCommunityPosts, deleteCommunityPost,
  type CommunityPost
} from '../api'
import { store } from '../store'
import PostDetailModal from '../components/PostDetailModal.vue'
import PublishPostModal from '../components/PublishPostModal.vue'

const posts = ref<CommunityPost[]>([])
const loading = ref(false)
const detailPostId = ref<number | null>(null)
const showPublish = ref(false)

async function load() {
  loading.value = true
  try {
    posts.value = await listCommunityPosts()
  } catch (e) {
    console.error('拉取答题圈帖子失败', e)
    store.showToast('拉取列表失败：' + (e as Error).message)
  } finally {
    loading.value = false
  }
}

onMounted(load)

// 发布成功后刷新
async function onPublished() {
  showPublish.value = false
  await load()
  store.showToast('已发布到答题圈 🎉')
}

async function onDelete(p: CommunityPost) {
  if (!p.mine) return
  if (!confirm(`确定删除帖子「${p.title}」？删除后无法恢复。`)) return
  await deleteCommunityPost(p.id)
  store.showToast('已删除')
  await load()
}

// 详情弹窗里删除/点赞/评论后也需要刷新一下列表（计数会变）
async function onDetailChanged() {
  await load()
}

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
  <div class="max-w-[860px] mx-auto">
    <!-- 顶部：标题 + 发布入口 -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-h1">📮 答题圈</h1>
        <p class="text-cap text-muted mt-1">分享你遇到的难题和解题思路，与大家一起讨论</p>
      </div>
      <button
        class="flex items-center gap-1.5 bg-qblue hover:opacity-90 text-white text-body font-semibold px-4 py-2 rounded-ctrl shadow-card transition"
        @click="showPublish = true"
      >
        <span class="text-lg leading-none">＋</span>发布题目
      </button>
    </div>

    <!-- 加载/空态 -->
    <div v-if="loading" class="bg-surface border border-line rounded-card p-10 text-center text-muted">
      加载中…
    </div>
    <div v-else-if="posts.length === 0" class="bg-surface border border-dashed border-line rounded-card p-10 text-center">
      <p class="text-3xl mb-2">💭</p>
      <p class="text-body text-body mb-3">答题圈还是空的，来当第一个分享者吧</p>
      <button class="text-qblue hover:underline" @click="showPublish = true">→ 发布一道题</button>
    </div>

    <!-- 帖子列表（CSDN 风格） -->
    <div v-else class="bg-surface border border-line rounded-card divide-y divide-line overflow-hidden">
      <article
        v-for="p in posts" :key="p.id"
        class="px-5 py-4 hover:bg-bg cursor-pointer transition relative group"
        @click="detailPostId = p.id"
      >
        <!-- 头部：头像 + 昵称 + 学科 -->
        <div class="flex items-center gap-2 mb-2">
          <span
            class="w-7 h-7 rounded-full flex items-center justify-center text-white text-cap font-bold shrink-0"
            :style="{ background: p.authorColor }"
          >{{ (p.authorName || '匿').slice(0, 1) }}</span>
          <span class="text-body text-body font-semibold truncate">{{ p.authorName }}</span>
          <span v-if="p.subject" class="text-cap px-1.5 py-0.5 rounded bg-cblue/10 text-qblue">{{ p.subject }}</span>
          <span class="text-cap text-muted ml-auto">{{ relativeTime(p.createdAt) }}</span>
        </div>

        <!-- 标题 -->
        <h3 class="text-h3 text-qblue font-semibold leading-snug mb-1.5 group-hover:underline">{{ p.title }}</h3>

        <!-- 摘要 -->
        <p class="text-body text-body line-clamp-2 leading-relaxed">{{ p.summary }}</p>

        <!-- 底部：阅读 / 点赞 / 评论 / 分享（我自己帖显示删除） -->
        <div class="flex items-center gap-5 mt-3 text-cap text-muted" @click.stop>
          <span class="flex items-center gap-1" title="阅读数">
            <span>👁</span><span>{{ p.viewCount }}</span>
          </span>
          <span class="flex items-center gap-1" :class="p.liked ? 'text-qblue' : ''" title="点赞">
            <span>{{ p.liked ? '👍' : '👍' }}</span><span>{{ p.likeCount }}</span>
          </span>
          <span class="flex items-center gap-1" title="评论">
            <span>💬</span><span>{{ p.commentCount }}</span>
          </span>
          <span class="flex items-center gap-1" title="转发">
            <span>🔗</span><span>{{ p.shareCount }}</span>
          </span>
          <button
            v-if="p.mine"
            class="ml-auto text-warn hover:underline"
            @click="onDelete(p)"
          >删除</button>
        </div>
      </article>
    </div>

    <!-- 详情浮窗 -->
    <PostDetailModal
      v-if="detailPostId !== null"
      :post-id="detailPostId"
      @close="detailPostId = null"
      @changed="onDetailChanged"
    />

    <!-- 发布浮窗 -->
    <PublishPostModal
      v-if="showPublish"
      @close="showPublish = false"
      @published="onPublished"
    />
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>