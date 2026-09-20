<template>
  <section class="hero">
    <!-- 背景大图：首屏 LCP 图片，eager + 高优先级加载；后端接口失败时回退到 .hero 的兜底渐变
         注意必须用动态 :src —— 静态 src 会被 SFC 编译器提升为 import，Vite 将按项目内文件解析导致报错 -->
    <img v-if="!bgFailed" class="hero-bg" :src="siteConfig.bgUrl" alt="" fetchpriority="high" decoding="async"
      @error="bgFailed = true" />
    <!-- 压暗渐变，保证文字与顶部导航可读 -->
    <div class="hero-scrim" aria-hidden="true"></div>

    <!-- 居中标题区 -->
    <div class="hero-content">
      <h1 class="hero-title">{{ siteConfig.title }}</h1>
      <p class="hero-subtitle">{{ displayed }}<span class="type-caret" aria-hidden="true"></span></p>
    </div>

    <!-- 底部波浪过渡：正反两组各两层，反相错速漂移，填充下一屏背景色 -->
    <div class="hero-wave" aria-hidden="true">
      <svg class="wave wave-far" viewBox="0 0 2880 160" preserveAspectRatio="none">
        <path :d="wavePathA" />
      </svg>
      <svg class="wave wave-back" viewBox="0 0 2880 160" preserveAspectRatio="none">
        <path :d="wavePathB" />
      </svg>
      <svg class="wave wave-mid" viewBox="0 0 2880 160" preserveAspectRatio="none">
        <path :d="wavePathB" />
      </svg>
      <svg class="wave wave-front" viewBox="0 0 2880 160" preserveAspectRatio="none">
        <path :d="wavePathA" />
      </svg>
    </div>

    <!-- 下滚指示器 -->
    <button class="scroll-indicator" type="button" aria-label="滚动到内容区" @click="scrollToContent">
      <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="2.4"
        stroke-linecap="round" stroke-linejoin="round">
        <path d="m6 9 6 6 6-6" />
      </svg>
    </button>
  </section>
</template>

<script setup lang="ts">
import siteConfig from '@/configs/siteConfig'
import { fetchPhrases } from '@/api/app'
import { onMounted, onUnmounted, ref } from 'vue'

// 后端背景图加载失败时隐藏 <img>，露出 .hero 的兜底渐变
const bgFailed = ref(false)

// 两相位波形（周期 1440，互为反相，大振幅：控制点贴近上下缘），叠加漂移形成交错波浪
const wavePathA =
  'M0,80 C240,160 480,0 720,80 C960,160 1200,0 1440,80 C1680,160 1920,0 2160,80 C2400,160 2640,0 2880,80 L2880,160 L0,160 Z'
const wavePathB =
  'M0,80 C240,0 480,160 720,80 C960,0 1200,160 1440,80 C1680,0 1920,160 2160,80 C2400,0 2640,160 2880,80 L2880,160 L0,160 Z'

// Hero 全局渲染在 App.vue，内容区 id 固定
function scrollToContent() {
  document.getElementById('page-content')?.scrollIntoView({ behavior: 'smooth' })
}

/* ---------- 副标题打字机 + 轮换 ---------- */
// 内置回退文案：后端 /api/App/phrases 不可用或返回空时使用
const FALLBACK_PHRASES = [
  '现代化 · 轻量级 · 开箱即用的 Vue 3 应用',
  '简洁优雅的 UI，极致的开发体验',
  '基于 Vue 3 + TypeScript + Vite 构建',
]

// 文案由后端下发，接口失败时保持回退值
const phrases = ref<string[]>(FALLBACK_PHRASES)
const phraseIndex = ref(0)
const displayed = ref('')
let typeTimer: ReturnType<typeof setTimeout> | undefined
let phrasesController: AbortController | undefined

onUnmounted(() => {
  clearTimeout(typeTimer)
  phrasesController?.abort()
})

onMounted(async () => {
  phrasesController = new AbortController()
  try {
    const remote = await fetchPhrases(phrasesController.signal)
    // 后端返回空数组时同样沿用回退文案，避免打字机拿到 undefined
    if (remote.length > 0) phrases.value = remote
  } catch {
    // 后端不可用/接口异常：静默沿用回退文案
  }
  // 文案请求期间组件已卸载，不再启动定时器
  if (phrasesController.signal.aborted) return

  startTypewriter()
})

function startTypewriter() {
  // 用户偏好减弱动态效果时，静态显示第一条
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    displayed.value = phrases.value[0] ?? ''
    return
  }

  let charIndex = 0
  let deleting = false

  const tick = () => {
    // phraseIndex 始终对 phrases.length 取模，且 phrases 非空，必然有值
    const current = phrases.value[phraseIndex.value]!

    if (!deleting) {
      charIndex++
      displayed.value = current.slice(0, charIndex)

      if (charIndex >= current.length) {
        deleting = true
        typeTimer = setTimeout(tick, 2400) // 整句显示后停留
        return
      }
      typeTimer = setTimeout(tick, 120) // 打字间隔
    } else {
      charIndex--
      displayed.value = current.slice(0, charIndex)

      if (charIndex <= 0) {
        deleting = false
        phraseIndex.value = (phraseIndex.value + 1) % phrases.value.length
        typeTimer = setTimeout(tick, 500) // 切换下一句的间隙
        return
      }
      typeTimer = setTimeout(tick, 50) // 删除比打字快
    }
  }

  typeTimer = setTimeout(tick, 800) // 首句开始前的等待
}
</script>

<style scoped>
.hero {
  position: relative;
  width: 100%;
  height: 100vh;
  height: 100svh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 背景图加载失败/加载中的兜底渐变（随主题色相低亮度着色，配合压暗层，白字始终可读） */
  background: linear-gradient(165deg, oklch(0.35 0.03 var(--hue)) 0%, oklch(0.24 0.03 var(--hue)) 55%, oklch(0.16 0.02 var(--hue)) 100%);
}

.hero-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  animation: hero-zoom 22s ease-in-out infinite alternate;
}

@keyframes hero-zoom {
  from {
    transform: scale(1);
  }

  to {
    transform: scale(1.06);
  }
}

.hero-scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg,
      rgba(0, 0, 0, 0.4),
      rgba(0, 0, 0, 0.14) 45%,
      rgba(0, 0, 0, 0.28) 100%);
}

.hero-content {
  position: relative;
  z-index: 2;
  text-align: center;
  color: #fff;
  padding: 0 24px;
}

.hero-title {
  font-size: clamp(2.75rem, 8vw, 5.5rem);
  line-height: 1.12;
  letter-spacing: 0.04em;
  font-weight: 700;
  text-shadow: 0 2px 16px rgba(0, 0, 0, 0.4);
}

.hero-subtitle {
  margin-top: 14px;
  font-size: clamp(1.05rem, 2.6vw, 1.4rem);
  letter-spacing: 0.06em;
  opacity: 0.94;
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.45);
  min-height: 1.7em;
  /* 打字/删除过程中高度稳定 */
}

/* 打字机光标 */
.type-caret {
  display: inline-block;
  width: 3px;
  height: 1.1em;
  margin-left: 5px;
  vertical-align: -0.18em;
  background: #fff;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.45);
  animation: caret-blink 1s step-end infinite;
}

@keyframes caret-blink {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0;
  }
}

/* ---------- 底部波浪 ---------- */
.hero-wave {
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 160px;
  z-index: 1;
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 200%;
  height: 100%;
  fill: var(--page-bg);
}

/* 正向组：front（实底）+ mid（半透明反相）；反向组：back + far
   各层高度不同 → 波峰 y 位置错开；负 animation-delay 错开水平相位 */
.wave-far {
  height: 134%;
  opacity: 0.3;
  animation: wave-drift 19s linear infinite reverse;
  animation-delay: -6s;
}

.wave-back {
  height: 122%;
  opacity: 0.5;
  animation: wave-drift 16s linear infinite reverse;
  animation-delay: -4s;
}

.wave-mid {
  height: 110%;
  opacity: 0.6;
  animation: wave-drift 14s linear infinite;
  animation-delay: -9s;
}

.wave-front {
  height: 100%;
  animation: wave-drift 11s linear infinite;
  animation-delay: -2s;
}

/* 波形以 1440 为周期，平移 50%（自身宽度的一半）实现无缝循环 */
@keyframes wave-drift {
  from {
    transform: translateX(0);
  }

  to {
    transform: translateX(-50%);
  }
}

/* ---------- 下滚指示器 ---------- */
.scroll-indicator {
  position: absolute;
  bottom: 180px;
  left: 50%;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  transition: background-color 0.2s;
  animation: scroll-bounce 1.8s ease-in-out infinite;
}

.scroll-indicator:hover {
  background: rgba(255, 255, 255, 0.3);
}

@keyframes scroll-bounce {

  0%,
  100% {
    transform: translate(-50%, 0);
  }

  50% {
    transform: translate(-50%, 9px);
  }
}

/* ---------- 响应式 ---------- */
@media (max-width: 768px) {
  .hero-wave {
    height: 96px;
  }

  .scroll-indicator {
    bottom: 108px;
  }

  /* 移动端长句会换行，预留两行高度避免跳动 */
  .hero-subtitle {
    min-height: 3.4em;
  }
}

/* 尊重系统减弱动态效果设置 */
@media (prefers-reduced-motion: reduce) {

  .hero-bg,
  .wave,
  .scroll-indicator,
  .type-caret {
    animation: none;
  }
}
</style>
