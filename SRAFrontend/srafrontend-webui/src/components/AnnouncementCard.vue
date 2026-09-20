<template>
  <div ref="rootEl" class="anno-card">
    <PanelCard title="公告">
      <!-- 加载中 -->
      <div v-if="loading" class="anno-state">
        <el-skeleton :rows="5" animated />
      </div>

      <!-- 加载失败：可重试 -->
      <div v-else-if="errorMsg" class="anno-state">
        <el-empty description="公告加载失败" :image-size="64">
          <el-button type="primary" size="small" @click="load">重试</el-button>
        </el-empty>
      </div>

      <el-empty v-else-if="!annos.length" description="暂无公告" :image-size="64" />

      <!-- 公告列表：点击查看详情 -->
      <ul v-else class="anno-list">
        <li v-for="(a, i) in annos" :key="i">
          <button type="button" class="anno-item" @click="openAnno(a)">
            <span class="anno-title">{{ a.title }}</span>
            <el-icon class="anno-arrow">
              <ArrowRight />
            </el-icon>
          </button>
        </li>
      </ul>
    </PanelCard>

    <!-- 公告详情弹窗：内置过渡动画，点击遮罩或关闭按钮均可关闭 -->
    <el-dialog v-model="dialogVisible" :title="activeAnno?.title" width="min(640px, calc(100vw - 32px))"
      class="anno-dialog">
      <!-- eslint-disable-next-line vue/no-v-html —— 内容已经 DOMPurify 净化 -->
      <div class="anno-markdown" v-html="activeContentHtml"></div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'
import { ArrowRight } from '@element-plus/icons-vue'
import { fetchAnnouncements } from '@/api/anno'
import type { Announcement } from '@/api/anno'
import { renderMarkdown } from '@/utils/markdown'
import PanelCard from './PanelCard.vue'

const annos = ref<Announcement[]>([])
const loading = ref(true)
const errorMsg = ref('')
const dialogVisible = ref(false)
const activeAnno = ref<Announcement | null>(null)
const rootEl = ref<HTMLElement | null>(null)

const activeContentHtml = computed(() =>
  activeAnno.value ? renderMarkdown(activeAnno.value.content) : '',
)

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await fetchAnnouncements()
    annos.value = data.announcements
  } catch (err) {
    errorMsg.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

function openAnno(a: Announcement) {
  activeAnno.value = a
  dialogVisible.value = true
}

// 懒加载：卡片进入视口后才发起请求（fetchAnnouncements 自带缓存，重进页面不重复请求）
onMounted(() => {
  const { stop } = useIntersectionObserver(
    rootEl,
    ([entry]) => {
      if (entry?.isIntersecting) {
        stop()
        load()
      }
    },
    { threshold: 0.1 },
  )
})
</script>

<style scoped>
.anno-state {
  padding: 8px 0;
}

.anno-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}

/* 列表项：悬停高亮 + 箭头位移 */
.anno-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.2s,
    color 0.2s;
}

.anno-item:hover {
  background: var(--color-background-mute);
  color: var(--color-heading);
}

.anno-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.anno-arrow {
  flex: none;
  opacity: 0.5;
  transition:
    transform 0.2s,
    color 0.2s,
    opacity 0.2s;
}

.anno-item:hover .anno-arrow {
  opacity: 1;
  transform: translateX(2px);
  color: var(--el-color-primary);
}

/* 弹窗内 Markdown 排版（v-html 内容需 :deep 穿透） */
.anno-markdown {
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text);
  overflow-wrap: break-word;
}

/* 首尾元素去边距，避免内容区上下留白不齐 */
.anno-markdown> :deep(:first-child) {
  margin-top: 0;
}

.anno-markdown> :deep(:last-child) {
  margin-bottom: 0;
}

/* base.css 全局重置了 font-weight: normal，加粗需显式恢复 */
.anno-markdown :deep(strong) {
  font-weight: 600;
  color: var(--color-heading);
}

.anno-markdown :deep(h1),
.anno-markdown :deep(h2),
.anno-markdown :deep(h3),
.anno-markdown :deep(h4) {
  color: var(--color-heading);
  font-weight: 600;
  margin: 0.6em 0 0.4em;
}

.anno-markdown :deep(h1) {
  font-size: 1.25em;
}

/* 二级标题加底部分隔线（GitHub 风格） */
.anno-markdown :deep(h2) {
  padding-bottom: 0.25em;
  border-bottom: 1px solid var(--color-border);
}

.anno-markdown :deep(h3) {
  font-size: 1.1em;
}

.anno-markdown :deep(h4) {
  font-size: 1em;
}

.anno-markdown :deep(p) {
  margin: 0.5em 0;
}

.anno-markdown :deep(ul),
.anno-markdown :deep(ol) {
  padding-left: 1.4em;
  margin: 0.4em 0;
}

.anno-markdown :deep(li) {
  margin: 0.2em 0;
}

.anno-markdown :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.9em;
  background: var(--color-background-mute);
  border-radius: 4px;
  padding: 1px 5px;
}

.anno-markdown :deep(pre) {
  background: var(--color-background-mute);
  border-radius: 8px;
  padding: 12px;
  overflow: auto;
}

.anno-markdown :deep(pre code) {
  background: transparent;
  padding: 0;
}

.anno-markdown :deep(a) {
  color: var(--el-color-primary);
  text-decoration: none;
}

.anno-markdown :deep(a:hover) {
  text-decoration: underline;
}

.anno-markdown :deep(blockquote) {
  margin: 0.5em 0;
  padding: 6px 12px;
  border-left: 3px solid var(--el-color-primary);
  border-radius: 0 8px 8px 0;
  background: var(--color-background-mute);
  color: var(--color-text);
}

.anno-markdown :deep(img) {
  max-width: 100%;
  border-radius: 8px;
}

.anno-markdown :deep(hr) {
  height: 1px;
  margin: 1em 0;
  border: 0;
  background: var(--color-border);
}

.anno-markdown :deep(table) {
  border-collapse: collapse;
  width: 100%;
}

.anno-markdown :deep(th),
.anno-markdown :deep(td) {
  border: 1px solid var(--color-border);
  padding: 6px 10px;
  text-align: left;
}

.anno-markdown :deep(th) {
  background: var(--color-background-mute);
  font-weight: 600;
}
</style>

<!-- 弹窗高度限制与外观：弹窗被 Teleport 到 body，需用非 scoped 样式命中 EP 内部结构 -->
<style>
/* 外壳：跟随主题的表面色 + 圆角边框阴影（与 PanelCard 同一设计语言） */
.el-dialog.anno-dialog {
  display: flex;
  flex-direction: column;
  max-height: calc(85vh - 32px);
  margin-bottom: 32px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm), var(--shadow-lg);
  overflow: hidden;
}

/* 头部：小圆点 + 标题，与 PanelCard 标题栏呼应 */
.el-dialog.anno-dialog .el-dialog__header {
  flex: none;
  display: flex;
  align-items: center;
  padding: 14px 18px;
  margin: 0;
  border-bottom: 1px solid var(--color-border);
}

.el-dialog.anno-dialog .el-dialog__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-heading);
}

/* 标题前的主题色小圆点 */
.el-dialog.anno-dialog .el-dialog__title::before {
  content: '';
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
  vertical-align: middle;
}

/* 关闭按钮：圆角方块，悬停浅色底 */
.el-dialog.anno-dialog .el-dialog__headerbtn {
  top: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  transition: background 0.2s;
}

.el-dialog.anno-dialog .el-dialog__headerbtn:hover {
  background: var(--color-background-mute);
}

/* 内容区填满剩余高度，超出时仅在弹窗内部滚动；细滚动条 */
.el-dialog.anno-dialog .el-dialog__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 18px;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-hover) transparent;
}

.el-dialog.anno-dialog .el-dialog__body::-webkit-scrollbar {
  width: 6px;
}

.el-dialog.anno-dialog .el-dialog__body::-webkit-scrollbar-thumb {
  border-radius: 3px;
  background: var(--color-border-hover);
}
</style>
