<script setup lang="ts">
import { onMounted } from 'vue'
import { store } from '../store'
import { AI_PROVIDERS } from '../types'
import ChatWindow from '../components/ChatWindow.vue'
import ApiKeyModal from '../components/ApiKeyModal.vue'

// 进入 AI 答疑页时确保至少有一个会话，避免右侧聊天区因无会话而空白
onMounted(async () => {
  if (!store.activeConv()) {
    try { await store.newConversation() }
    catch (e) { console.error('自动创建首个会话失败', e) }
  }
})
</script>

<template>
  <div class="flex gap-6 items-stretch" style="height: calc(100vh - 140px); min-height: 360px">
    <!-- 左：历史对话（桌面） -->
    <aside class="hidden md:flex flex-col w-[240px] flex-shrink-0 border border-line rounded-card bg-surface p-4 h-full overflow-y-auto">
      <div class="text-cap text-muted mb-3">历史对话</div>
      <div
        v-for="c in store.conversations" :key="c.id"
        class="rounded-ctrl px-2.5 py-2 cursor-pointer text-body truncate transition"
        :class="store.activeConvId === c.id ? 'bg-cblue/10 text-qblue font-semibold' : 'hover:bg-bg'"
        @click="store.activeConvId = c.id"
      >{{ c.title }}</div>
      <div
        class="mt-4 text-center border border-dashed border-line rounded-ctrl py-2 text-cap text-body cursor-pointer hover:border-qblue hover:text-qblue transition"
        @click="store.newConversation()"
      >＋ 新建对话</div>
    </aside>

    <!-- 右：聊天区 -->
    <div class="flex-1 flex flex-col min-w-0 h-full">
      <!-- 移动端会话横向切换 -->
      <div class="md:hidden mb-3 flex gap-2 overflow-x-auto pb-1">
        <button
          v-for="c in store.conversations" :key="c.id"
          class="text-cap border rounded-tag px-2.5 py-1 whitespace-nowrap transition"
          :class="store.activeConvId === c.id ? 'bg-qblue text-white border-qblue' : 'border-line text-body'"
          @click="store.activeConvId = c.id"
        >{{ c.title }}</button>
        <button class="text-cap border border-dashed rounded-tag px-2.5 py-1 text-body" @click="store.newConversation()">＋ 新建</button>
      </div>

      <ChatWindow
        :messages="store.activeConv()?.messages ?? []"
        :providers="AI_PROVIDERS"
        :current="store.aiProvider"
        @send="(t: string) => store.sendStream(t)"
        @provider-change="(p) => store.setProvider(p)"
        @open-keys="store.openApiKeys()"
      />
    </div>

    <!-- 全局 API 密钥设置弹窗 -->
    <ApiKeyModal v-if="store.apiKeysOpen" />
  </div>
</template>