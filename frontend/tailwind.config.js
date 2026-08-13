/** Recall UI Design System Token → Tailwind theme 映射
 *  源规范：recall-page-generator Skill §3（文字/语义色/内容区标识/8色分类/间距/圆角/字号/字体）
 */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        // 文字层级
        ink: '#1D1D1F', body: '#6E6E73', muted: '#AEAEB2',
        // 语义色
        success: '#34C759', warning: '#FF9500', danger: '#FF3B30',
        // 内容区标识（主操作色）
        qblue: '#3B82F6', agreen: '#10B981',
        // 错题本 8 色分类
        cblue: '#3B82F6', cgreen: '#10B981', corange: '#FF9500', cpurple: '#AF52DE',
        cpink: '#FF2D55', ccyan: '#64D2FF', camber: '#FFCC00', cindigo: '#5E5CE6',
        // 中性
        line: '#E5E5EA', surface: '#FFFFFF', bg: '#F5F5F7'
      },
      spacing: {
        xs: '4px', sm: '8px', md: '12px', lg: '16px', xl: '24px', x2: '32px'
      },
      borderRadius: {
        tag: '6px', ctrl: '8px', card: '12px'
      },
      fontSize: {
        h1: ['28px', { lineHeight: '1.3', fontWeight: '600' }],
        h2: ['20px', { lineHeight: '1.4', fontWeight: '600' }],
        body: ['14px', { lineHeight: '1.6', fontWeight: '400' }],
        cap: ['12px', { lineHeight: '1.5', fontWeight: '400' }]
      },
      fontFamily: {
        sans: ['"PingFang SC"', '"钉钉进步体"', '"DingTalk JinBuTi"', '"SF Pro Text"', '-apple-system', 'sans-serif']
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,.04), 0 4px 16px rgba(0,0,0,.05)'
      }
    }
  },
  plugins: []
}
