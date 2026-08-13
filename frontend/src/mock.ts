import type { Category, Mistake, Conversation } from './types'

/** 前端演示用 mock 数据（后端未启动时 VITE_USE_MOCK 默认开启） */
export const mockCategories: Category[] = [
  { id: 0, name: '全部错题', color: '#6E6E73', count: 128 },
  { id: 1, name: '数学', color: '#3B82F6', count: 42 },
  { id: 2, name: '物理', color: '#AF52DE', count: 31 },
  { id: 3, name: '英语', color: '#FF2D55', count: 28 },
  { id: 4, name: '化学', color: '#10B981', count: 19 },
  { id: 5, name: '我的收藏', color: '#FFCC00', count: 12 },
]

export const mockMistakes: Mistake[] = [
  {
    id: 1, categoryId: 1, subject: '数学',
    content: '已知函数 f(x)=x³−3x，求其在 x=1 处的切线方程，并判断单调性。',
    knowledgePoints: ['导数', '切线', '单调性'],
    source: '期中月考', reviewCount: 3, reviewed: true,
    aiAnalysis: 'f\'(x)=3x²−3，f\'(1)=0 为斜率；f(1)=−2，故切线 y=−2。令 f\'(x)=0 得 x=±1，在 (−∞,−1)∪(1,+∞) 上单调递增，(−1,1) 上单调递减。',
    createdAt: '2026-08-01T10:00:00'
  },
  {
    id: 2, categoryId: 2, subject: '物理',
    content: '光滑水平面上物体受恒力 F 作用，质量 m，求 t 秒后的位移与速度。',
    knowledgePoints: ['牛顿第二定律', '匀加速直线运动'],
    source: '课堂练习', reviewCount: 1, reviewed: false,
    aiAnalysis: 'a=F/m；v=at=Ft/m；x=½at²=Ft²/2m。注意初速度为 0，方向与 F 同向。',
    createdAt: '2026-08-06T15:20:00'
  },
  {
    id: 3, categoryId: 3, subject: '英语',
    content: 'The teacher insisted that he ___ (go) to school on time. 用所给词适当形式填空。',
    knowledgePoints: ['虚拟语气', 'insist'],
    source: '英语周测', reviewCount: 5, reviewed: true,
    aiAnalysis: '填 (should) go。insist 表“坚持要求”时，宾语从句用 (should)+动词原形；表“坚持认为”时才用陈述语气。',
    createdAt: '2026-08-03T09:12:00'
  },
  {
    id: 4, categoryId: 4, subject: '化学',
    content: '用 0.1mol/L NaOH 滴定 20.00mL 未知浓度 HCl，终点耗碱 20.00mL，求 HCl 浓度。',
    knowledgePoints: ['酸碱中和滴定', '物质的量浓度'],
    source: '实验报告', reviewCount: 0, reviewed: false,
    aiAnalysis: 'c(HCl)·V(HCl)=c(NaOH)·V(NaOH)，c=0.1×20.00/20.00=0.1mol/L。注意滴定管读数与指示剂选择。',
    createdAt: '2026-08-08T18:45:00'
  },
  {
    id: 5, categoryId: 1, subject: '数学',
    content: '求不定积分 ∫(2x+1)dx 并验证。',
    knowledgePoints: ['积分', '原函数'],
    source: '课后作业', reviewCount: 2, reviewed: true,
    aiAnalysis: '∫(2x+1)dx=x²+x+C。验证：(x²+x+C)\'=2x+1 ✓。',
    createdAt: '2026-08-02T20:00:00'
  }
]

let seq = 100
export function nextId() { return ++seq }

export const mockConversations: Conversation[] = [
  {
    id: 1, title: '导数切线问题求解',
    messages: [
      { id: 1, role: 'user', content: '这道导数题在 x=1 处切线怎么求？', createdAt: '2026-08-10T19:00:00' },
      { id: 2, role: 'assistant', content: '先求导 f\'(x)=3x²−3，代入 x=1 得斜率 f\'(1)=0；再算 f(1)=−2，切线方程即 y=−2。需要我出一道同考点变式题吗？', createdAt: '2026-08-10T19:00:02' }
    ]
  },
  {
    id: 2, title: '牛顿第二定律错题',
    messages: [
      { id: 3, role: 'user', content: '恒力作用下位移怎么算？', createdAt: '2026-08-09T21:30:00' },
      { id: 4, role: 'assistant', content: '先用 F=ma 求加速度 a，初速度 v0=0 时：v=at，x=½at²。把 a=F/m 代入即可。', createdAt: '2026-08-09T21:30:05' }
    ]
  },
  {
    id: 3, title: '虚拟语气语法点',
    messages: [
      { id: 5, role: 'user', content: 'insist 后面从句用什么语气？', createdAt: '2026-08-08T11:00:00' },
      { id: 6, role: 'assistant', content: 'insist 表“坚持要求”→(should)+动词原形；表“坚持认为”→陈述语气。建议加入「虚拟语气」专项复习。', createdAt: '2026-08-08T11:00:04' }
    ]
  }
]
