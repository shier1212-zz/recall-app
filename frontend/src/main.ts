import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { store } from './store'
import './style.css'

/** 全局错误兜底：避免任何运行时报错导致整页白屏。
 *  把错误信息以醒目红框显式写到 DOM，让用户/调试者一眼看到根因。 */
function showFatal(msg: string, stack?: string) {
  if (typeof document === 'undefined') return
  let el = document.getElementById('__wb_fatal')
  if (!el) {
    el = document.createElement('div')
    el.id = '__wb_fatal'
    el.style.cssText = [
      'position:fixed', 'left:24px', 'right:24px', 'top:80px', 'z-index:99999',
      'background:#fff1f2', 'border:2px solid #f43f5e', 'color:#9f1239',
      'border-radius:12px', 'padding:16px 20px',
      'font:13px/1.6 ui-monospace,Menlo,monospace',
      'white-space:pre-wrap', 'word-break:break-word',
      'box-shadow:0 10px 30px rgba(0,0,0,.15)'
    ].join(';')
    document.body.appendChild(el)
  }
  el.textContent = (el.textContent ? el.textContent + '\n\n' : '') + msg + (stack ? '\n\n' + stack : '')
}
window.addEventListener('error', (e) => {
  const msg = (e?.error?.stack || e?.error?.message || e?.message || '未知错误') as string
  showFatal('❌ 前端运行时错误：' + msg)
})
window.addEventListener('unhandledrejection', (e) => {
  const r: any = e?.reason
  const msg = (r?.stack || r?.message || String(r) || '未知错误') as string
  showFatal('❌ 未捕获的 Promise 错误：' + msg)
})

try {
  createApp(App).use(router).mount('#app')
  void store.init()
} catch (e: any) {
  showFatal('❌ Vue 挂载失败：' + (e?.stack || e?.message || String(e)))
}
