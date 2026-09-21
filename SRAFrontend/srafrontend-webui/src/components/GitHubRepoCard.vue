<template>
  <!-- GitHub 仓库卡：参考 GitHub 官方仓库卡片样式（紧凑单色、小头像、Octocat 徽标、图标统计行） -->
  <section class="repo-card">
    <!-- 加载中：骨架屏占位 -->
    <div v-if="loading" class="repo-loading">
      <el-skeleton animated :rows="2" />
    </div>

    <template v-else>
      <!-- 头部：小头像 + owner / 仓库名 + 右上 GitHub 徽标 -->
      <header class="repo-head">
        <img
          v-if="info.ownerAvatar"
          :src="info.ownerAvatar"
          :alt="info.owner"
          class="repo-avatar"
        />
        <span v-else class="repo-avatar repo-avatar-fallback" aria-hidden="true">
          <svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor">
            <path :d="OCTICON_MARK_GITHUB" />
          </svg>
        </span>

        <a class="repo-link" :href="repoUrl" target="_blank" rel="noopener noreferrer">
          <span class="repo-owner">{{ info.owner }}</span>
          <span class="repo-slash" aria-hidden="true">/</span>
          <span class="repo-name">{{ repoName }}</span>
        </a>

        <a
          class="repo-github"
          :href="repoUrl"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="`在 GitHub 上查看 ${repoName}`"
        >
          <svg viewBox="0 0 16 16" width="20" height="20" fill="currentColor" aria-hidden="true">
            <path :d="OCTICON_MARK_GITHUB" />
          </svg>
        </a>
      </header>

      <!-- 描述 -->
      <p class="repo-desc">{{ info.description }}</p>
      <p v-if="fetchError" class="repo-fallback-hint">实时信息获取失败，展示本地配置</p>

      <!-- 统计行：Star / Fork / License -->
      <ul class="repo-stats">
        <li class="stat">
          <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true">
            <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z"></path>
          </svg>
          <span>{{ remote ? formatCount(info.stars) : '—' }}</span>
        </li>
        <li class="stat">
          <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true">
            <path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"></path>
          </svg>
          <span>{{ remote ? formatCount(info.forks) : '—' }}</span>
        </li>
        <li class="stat">
          <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true">
            <path d="M8.75.75V2h.985c.304 0 .603.08.867.231l1.29.736c.038.022.08.033.124.033h2.234a.75.75 0 0 1 0 1.5h-.427l2.111 4.692a.75.75 0 0 1-.154.838l-.53-.53.529.531-.001.002-.002.002-.006.006-.006.005-.01.01-.045.04c-.21.176-.441.327-.686.45C14.556 10.78 13.88 11 13 11a4.498 4.498 0 0 1-2.023-.454 3.544 3.544 0 0 1-.686-.45l-.045-.04-.016-.015-.006-.006-.004-.004v-.001a.75.75 0 0 1-.154-.838L12.178 4.5h-.162c-.305 0-.604-.079-.868-.231l-1.29-.736a.245.245 0 0 0-.124-.033H8.75V13h2.5a.75.75 0 0 1 0 1.5h-6.5a.75.75 0 0 1 0-1.5h2.5V3.5h-.984a.245.245 0 0 0-.124.033l-1.289.737c-.265.15-.564.23-.869.23h-.162l2.112 4.692a.75.75 0 0 1-.154.838l-.53-.53.529.531-.001.002-.002.002-.006.006-.016.015-.045.04c-.21.176-.441.327-.686.45C4.556 10.78 3.88 11 3 11a4.498 4.498 0 0 1-2.023-.454 3.544 3.544 0 0 1-.686-.45l-.045-.04-.016-.015-.006-.006-.004-.004v-.001a.75.75 0 0 1-.154-.838L2.178 4.5H1.75a.75.75 0 0 1 0-1.5h2.234a.249.249 0 0 0 .125-.033l1.288-.737c.265-.15.564-.23.869-.23h.984V.75a.75.75 0 0 1 1.5 0Zm2.945 8.477c.285.135.718.273 1.305.273s1.02-.138 1.305-.273L13 6.327Zm-10 0c.285.135.718.273 1.305.273s1.02-.138 1.305-.273L3 6.327Z"></path>
          </svg>
          <span>{{ info.license || '—' }}</span>
        </li>
      </ul>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { fetchRepoInfo, GITHUB_REPO_SLUG } from '@/api/github'
import type { GitHubRepoInfo } from '@/api/github'
import siteConfig from '@/configs/siteConfig'

// GitHub 官方 Octicons（MIT 许可）内联 path，避免引入图标库依赖
const OCTICON_MARK_GITHUB =
  'M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z'

const repoUrl = siteConfig.repoUrl

/** 仓库名取自 siteConfig.repoUrl 的解析结果（与 API 请求地址同源），GitHub 请求失败时以作者名兜底 */
const repoName = GITHUB_REPO_SLUG.split('/')[1] || siteConfig.author

const remote = ref<GitHubRepoInfo | null>(null)
const loading = ref(true)
const fetchError = ref(false)

/** 展示数据：GitHub 实时信息优先，siteConfig 本地配置兜底 */
const info = computed(() => ({
  owner: remote.value?.owner || siteConfig.author,
  ownerAvatar: remote.value?.ownerAvatar ?? '',
  description: remote.value?.description || siteConfig.description,
  stars: remote.value?.stars ?? 0,
  forks: remote.value?.forks ?? 0,
  license: remote.value?.license || siteConfig.license,
}))

/** 千位以上缩写为 k（如 1.2k），其余原样展示 */
function formatCount(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

let controller: AbortController | null = null

onMounted(async () => {
  controller = new AbortController()
  try {
    remote.value = await fetchRepoInfo(controller.signal)
  } catch (err) {
    // 组件卸载导致的中断不算失败
    if ((err as Error).name !== 'AbortError') fetchError.value = true
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => controller?.abort())
</script>

<style scoped>
/* 卡片外壳：与 PanelCard 同一设计语言（surface 底、12px 圆角、token 阴影），无标题头 */
.repo-card {
  display: block;
  height: 100%;
  padding: 16px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  transition:
    border-color 0.25s ease,
    background-color 0.25s ease,
    box-shadow 0.25s ease,
    transform 0.25s ease;
}

/* hover：边框点亮 + 背景微调 + 上浮加深阴影 */
.repo-card:hover {
  background: var(--color-background-soft);
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

.repo-loading {
  padding: 8px 0;
}

/* ---------- 头部 ---------- */
.repo-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.repo-avatar {
  flex: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  object-fit: cover;
}

/* 头像缺失时的兜底：GitHub 徽标占位 */
.repo-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-background-mute);
  color: var(--color-text-secondary);
}

.repo-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  text-decoration: none;
  font-size: 15px;
}

.repo-owner {
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.repo-slash {
  color: var(--color-muted);
}

.repo-name {
  color: var(--color-heading);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s;
}

/* 名称整体 hover 时仓库名点亮主色 */
.repo-link:hover .repo-name,
.repo-link:hover .repo-owner {
  color: var(--color-primary);
}

/* 右上 GitHub 徽标链接 */
.repo-github {
  flex: none;
  display: flex;
  margin-left: auto;
  color: var(--color-text-secondary);
  transition: color 0.2s;
}

.repo-github:hover {
  color: var(--color-primary);
}

/* ---------- 描述 ---------- */
.repo-desc {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  transition: color 0.25s ease;
}

/* 卡片 hover 时描述文字点亮 */
.repo-card:hover .repo-desc {
  color: var(--color-text);
}

.repo-fallback-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-muted);
}

/* ---------- 统计行 ---------- */
.repo-stats {
  display: flex;
  align-items: center;
  gap: 20px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-heading);
  font-variant-numeric: tabular-nums;
  transition: color 0.25s ease;
}

.stat svg {
  flex: none;
  color: var(--color-muted);
  transition: color 0.25s ease;
}

/* 卡片 hover 时统计图标点亮主色 */
.repo-card:hover .stat svg {
  color: var(--color-primary);
}
</style>
