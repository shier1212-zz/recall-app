import { createRouter, createWebHistory } from 'vue-router'
import MistakeBookView from './views/MistakeBookView.vue'
import AiChatView from './views/AiChatView.vue'
import DashboardView from './views/DashboardView.vue'
import HelpView from './views/HelpView.vue'
import ReviewView from './views/ReviewView.vue'

/** 未匹配路由的兜底（避免白屏） */
const NotFound = {
  template: '<div class="max-w-[1180px] mx-auto p-8 text-center text-body"><p class="text-3xl mb-3">🧭</p><p>页面找不到了，回到 <router-link to="/" class="text-qblue underline">错题集</router-link></p></div>'
}

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: MistakeBookView },
    { path: '/review', name: 'review', component: ReviewView },
    { path: '/ai', name: 'ai', component: AiChatView },
    { path: '/dashboard', name: 'dashboard', component: DashboardView },
    { path: '/help', name: 'help', component: HelpView },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFound }
  ]
})
