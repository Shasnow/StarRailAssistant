<template>
  <header class="nav-bar" :class="{ 'over-hero': overHero }">
    <div class="nav-inner">
      <!-- 左侧：logo + 项目名称 -->
      <RouterLink to="/" class="nav-brand" @click="menuOpen = false">
        <img :src="siteConfig.logo" alt="logo" class="nav-logo" />
        <span class="nav-title">{{ siteConfig.title }}</span>
      </RouterLink>

      <!-- 中间：路由导航链接（桌面端），图标来自路由 meta.icon -->
      <nav class="nav-center">
        <RouterLink v-for="route in routes" :key="route.path" :to="route.path" class="nav-link">
          <el-icon v-if="route.icon" class="link-icon">
            <component :is="route.icon" />
          </el-icon>
          {{ route.name }}
        </RouterLink>
      </nav>

      <!-- 右侧：用户状态 -->
      <div class="nav-right">
        <div class="user-info">
          <span class="avatar" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path
                d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5Zm0 2c-3.33 0-10 1.67-10 5v1a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-1c0-3.33-6.67-5-10-5Z" />
            </svg>
          </span>
          <span class="status">
            <span class="status-dot" :class="status"></span>
            {{ status }}
          </span>
        </div>

        <!-- 主题色相选择 -->
        <ThemeHuePicker />

        <!-- 深色模式切换 -->
        <button class="theme-toggle" :aria-label="isDark ? '切换到浅色模式' : '切换到深色模式'" @click="toggleTheme($event)">
          <svg v-if="isDark" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
            stroke-width="2" stroke-linecap="round">
            <circle cx="12" cy="12" r="4" />
            <path
              d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
          </svg>
          <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
          </svg>
        </button>

        <!-- 移动端汉堡按钮 -->
        <button class="hamburger" :class="{ open: menuOpen }" aria-label="切换菜单" @click="menuOpen = !menuOpen">
          <span></span><span></span><span></span>
        </button>
      </div>
    </div>

    <!-- 移动端下拉菜单 -->
    <nav v-show="menuOpen" class="mobile-menu">
      <RouterLink v-for="route in routes" :key="route.path" :to="route.path" class="mobile-link"
        @click="menuOpen = false">
        <el-icon v-if="route.icon" class="link-icon">
          <component :is="route.icon" />
        </el-icon>
        {{ route.name }}
      </RouterLink>
    </nav>
  </header>
</template>

<script lang="ts" setup>
import { computed, nextTick, ref } from 'vue'
import { useDark, useToggle, useWindowScroll } from '@vueuse/core'
import { useRouter } from 'vue-router'
import siteConfig from '@/configs/siteConfig'
import ThemeHuePicker from './ThemeHuePicker.vue'

const router = useRouter()
const status = ref('online')
const menuOpen = ref(false)

const { y: scrollY } = useWindowScroll()
// Hero 全局渲染：页面顶部时导航栏透明，滚动后切回毛玻璃
const overHero = computed(() => scrollY.value <= 24 && !menuOpen.value)

/* ---------- 主题切换 ---------- */
// useDark：切换 <html> 的 dark 类（对应 base.css 的 :root.dark），初始取本地存储 > 系统偏好
const isDark = useDark({ storageKey: 'theme' })
const toggleDark = useToggle(isDark)

// 以鼠标位置为圆心的圆形揭示过渡（View Transitions API）：
// 浅→深：旧（浅色）视图向按钮收缩；深→浅：新（浅色）视图从按钮扩张
// 动画本身由 base.css 中按 data-theme-transition 属性匹配的 CSS 动画驱动
function toggleTheme(event: MouseEvent) {
  const { clientX: x, clientY: y } = event

  // 浏览器不支持 View Transitions 时直接切换
  if (!document.startViewTransition) {
    toggleDark()
    return
  }

  const root = document.documentElement
  const theme = isDark.value ? 'to-light' : 'to-dark'
  const radius = Math.hypot(
    Math.max(x, innerWidth - x),
    Math.max(y, innerHeight - y)
  )

  // 设置圆心/半径与过渡方向，驱动 base.css 中对应的 clip-path 动画
  root.style.setProperty('--theme-transition-x', `${x}px`)
  root.style.setProperty('--theme-transition-y', `${y}px`)
  root.style.setProperty('--theme-transition-radius', `${radius}px`)
  root.dataset.themeTransition = theme

  const transition = document.startViewTransition(async () => {
    toggleDark()
    // 确保 dark 类应用到 DOM 后再捕获新视图
    await nextTick()
  })

  // 过渡结束后移除方向属性，避免残留规则影响其他 View Transition；
  // 快速连点时属性已被新过渡重新设置，此时跳过删除
  transition.finished.finally(() => {
    if (root.dataset.themeTransition === theme) {
      delete root.dataset.themeTransition
    }
  })
}

// 导航路由清单：图标组件直接由路由 meta 携带（见 router/index.ts 的 RouteMeta 扩展），
// 登录等全屏独立页用 meta.hideInNav 排除
const routes = router
  .getRoutes()
  .filter((item) => !item.meta.hideInNav)
  .map((item) => ({
    path: item.path,
    name: item.name,
    icon: item.meta.icon,
  }))
</script>

<style scoped>
.nav-bar {
  --nav-height: 60px;
  --nav-radius: 16px;
  --nav-bg: rgba(255, 255, 255, 0.72);

  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--nav-bg);
  backdrop-filter: blur(12px) saturate(1.6);
  -webkit-backdrop-filter: blur(12px) saturate(1.6);
  border-bottom: 1px solid var(--color-border);
  border-bottom-left-radius: var(--nav-radius);
  border-bottom-right-radius: var(--nav-radius);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition:
    background-color 0.3s,
    border-color 0.3s,
    box-shadow 0.3s;
}

html.dark .nav-bar {
  --nav-bg: rgba(24, 24, 24, 0.72);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

/* ---------- 覆盖在 Hero 之上：全透明 + 白色文字 ---------- */
.nav-bar.over-hero {
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border-bottom-color: transparent;
  box-shadow: none;
}

.nav-bar.over-hero .nav-title,
.nav-bar.over-hero .nav-link,
.nav-bar.over-hero .status {
  color: #fff;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
}

.nav-bar.over-hero .nav-link:hover,
.nav-bar.over-hero .nav-link.router-link-exact-active {
  color: #fff;
  background: rgba(255, 255, 255, 0.18);
}

.nav-bar.over-hero .nav-logo {
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.45));
}

.nav-bar.over-hero .avatar {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.nav-bar.over-hero .theme-toggle,
.nav-bar.over-hero :deep(.hue-toggle) {
  color: #fff;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
}

.nav-bar.over-hero .hamburger span {
  background: #fff;
}

/* ---------- 大屏：导航栏悬浮居中，不横跨整页 ---------- */
@media (min-width: 1200px) {
  .nav-bar {
    top: 12px;
    left: 50%;
    right: auto;
    transform: translateX(-50%);
    width: min(1200px, calc(100% - 48px));
    border: 1px solid var(--color-border);
    border-radius: var(--nav-radius);
  }

  .nav-bar.over-hero {
    border-color: transparent;
  }
}

.nav-inner {
  display: flex;
  align-items: center;
  gap: 24px;
  height: var(--nav-height);
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ---------- 左侧 ---------- */
.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--color-heading);
}

.nav-logo {
  width: 28px;
  height: 28px;
}

.nav-title {
  font-size: 19px;
  font-weight: 600;
}

/* ---------- 中间 ---------- */
.nav-center {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 8px;
  font-size: 16px;
  color: var(--color-text);
  text-decoration: none;
  transition:
    background-color 0.2s,
    color 0.2s;
}

/* 图标随链接文字变色（Element Plus 图标默认 1em，用 font-size 控制大小） */
.link-icon {
  font-size: 17px;
}

.nav-link:hover {
  color: var(--color-primary);
  background: var(--color-background-mute);
}

.nav-link.router-link-exact-active {
  color: var(--color-primary);
  background: var(--color-background-mute);
  font-weight: 600;
}

/* ---------- 右侧 ---------- */
.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
  /* 移动端 nav-center 隐藏后仍贴住导航栏右缘 */
  margin-left: auto;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-background-mute);
  color: var(--color-text);
}

.status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--color-muted);
}

.status-dot.online {
  background: var(--color-success);
  box-shadow: 0 0 4px color-mix(in srgb, var(--color-success) 60%, transparent);
}

/* ---------- 主题切换按钮 ---------- */
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  transition:
    background-color 0.2s,
    color 0.2s;
}

.theme-toggle:hover {
  color: var(--color-primary);
  background: var(--color-background-mute);
}

/* ---------- 汉堡按钮 ---------- */
.hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 40px;
  height: 40px;
  padding: 8px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
}

.hamburger span {
  display: block;
  width: 100%;
  height: 2px;
  border-radius: 2px;
  background: var(--color-text);
  transition:
    transform 0.25s,
    opacity 0.25s;
}

.hamburger.open span:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}

.hamburger.open span:nth-child(2) {
  opacity: 0;
}

.hamburger.open span:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

/* ---------- 移动端菜单 ---------- */
.mobile-menu {
  display: flex;
  flex-direction: column;
  padding: 8px 16px 16px;
  animation: slide-down 0.2s ease;
}

.mobile-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 13px 14px;
  border-radius: 8px;
  font-size: 16px;
  color: var(--color-text);
  text-decoration: none;
  transition:
    background-color 0.2s,
    color 0.2s;
}

.mobile-link:hover,
.mobile-link.router-link-exact-active {
  color: var(--color-primary);
  background: var(--color-background-mute);
}

@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ---------- 响应式 ---------- */
@media (max-width: 768px) {
  .nav-center {
    display: none;
  }

  .status {
    display: none;
  }

  .hamburger {
    display: flex;
  }
}
</style>
