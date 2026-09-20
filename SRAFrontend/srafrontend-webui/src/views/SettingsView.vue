<template>
  <div class="settings-page">
    <!-- schema 加载中 -->
    <div v-if="loading" class="page-state">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- schema 加载失败：可重试 -->
    <div v-else-if="errorMsg" class="page-state">
      <el-empty description="加载设置项失败" :image-size="72">
        <div class="error-detail">{{ errorMsg }}</div>
        <el-button type="primary" @click="load">重试</el-button>
      </el-empty>
    </div>

    <!-- 左右分栏：左侧导航（固定宽度、吸顶）+ 右侧设置内容 -->
    <div v-else class="settings-layout">
      <aside class="nav-col">
        <SettingsNavCard :sections="sections" :active-key="activeKey" @select="selectAnchor" />
      </aside>

      <section class="content-col">
        <!-- 后端设置读取失败：不阻塞表单展示（仅展示 schema 默认值），可重试 -->
        <el-alert v-if="settingsError" class="settings-alert" type="error" :title="settingsError" :closable="false">
          <el-button size="small" @click="loadSettings">重试</el-button>
        </el-alert>

        <!-- 每个 section 一张卡片，字段挂 data-anchor 供导航定位 -->
        <SettingsSectionCard v-for="section in sections" :key="section.key" class="section-card" :model="model"
          :section-key="section.key" :label="section.label" :node="section.node" :doc="doc"
          :baseline="baselineModel ? baselineModel[section.key] : undefined" />

        <!-- 保存：仅提交有改动的 section（后端支持按字段部分更新） -->
        <div class="settings-footer">
          <span class="footer-hint">{{ footerHint }}</span>
          <el-button type="primary" size="small" :disabled="!isDirty" :loading="saving" @click="save">
            保存设置
          </el-button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { fetchOpenApiSpec } from '@/api/openapi'
import { fetchSettings, updateSettings } from '@/api/settings'
import type { AppSettingsPayload } from '@/api/settings'
import SettingsNavCard from '@/components/SettingsNavCard.vue'
import type { NavSection } from '@/components/SettingsNavCard.vue'
import SettingsSectionCard from '@/components/SettingsSectionCard.vue'
import type { OpenApiDocument, SchemaNode } from '@/utils/schemaForm'
import { buildDefaultModel, resolveNode, stableStringify } from '@/utils/schemaForm'

/** AppSettings 在 OpenAPI 规范中的引用路径 */
const SETTINGS_REF = '#/components/schemas/AppSettings'

/** 滚动定位时预留的顶部偏移：固定导航栏 60px + 间距 */
const SCROLL_OFFSET = 84

/** 导航分组 + 该分组的 schema 节点（节点仅内容区使用） */
interface ViewSection extends NavSection {
  node: SchemaNode
}

const doc = ref<OpenApiDocument | null>(null)
const loading = ref(true)
const errorMsg = ref('')
/** 后端设置读取失败信息（schema 仍可用，仅提示） */
const settingsError = ref('')
const saving = ref(false)

/** 设置模型：按 schema 结构构建默认值，再由后端真实设置覆盖；字段值随表单实时写入 */
const model = reactive<AppSettingsPayload>({})

/** 当前选中的大类（section key），由内容区滚动位置驱动 */
const activeKey = ref('')

/* ---------- 导航结构：AppSettings 的大类（section） ---------- */
const sections = computed<ViewSection[]>(() => {
  const d = doc.value
  if (!d) return []
  const root = resolveNode(d, { $ref: SETTINGS_REF })
  return Object.entries(root.properties ?? {}).map(([key, node]) => {
    const resolved = resolveNode(d, node)
    return {
      key,
      label: resolved.description ?? node.description ?? key,
      node,
    }
  })
})

/* ---------- 未保存更改检测：baseline 为最近一次加载/保存成功后的快照 ---------- */
const baseline = ref('')

const baselineModel = computed<AppSettingsPayload | null>(() =>
  baseline.value ? (JSON.parse(baseline.value) as AppSettingsPayload) : null,
)

const dirtyKeys = computed<Set<string>>(() => {
  const base = baselineModel.value
  if (!base) return new Set()
  const set = new Set<string>()
  for (const key of Object.keys(model)) {
    if (stableStringify(model[key]) !== stableStringify(base[key])) set.add(key)
  }
  return set
})

const isDirty = computed(() => dirtyKeys.value.size > 0)

const footerHint = computed(() => {
  if (!baseline.value) return '设置尚未加载'
  if (!isDirty.value) return '设置已是最新'
  const labels = sections.value.filter((s) => dirtyKeys.value.has(s.key)).map((s) => s.label)
  return `有未保存的更改：${labels.join('、')}`
})

/* ---------- 滚动联动：点击导航定位 + 滚动时反向高亮导航项 ---------- */
let spyFrame = 0
/** 平滑滚动的抑制窗口：避免滚动途中的中间位置把选中态抢走 */
let suppressSpyUntil = 0

function selectAnchor(anchor: string) {
  activeKey.value = anchor
  const el = document.querySelector<HTMLElement>(`[data-anchor="${anchor}"]`)
  if (!el) return
  suppressSpyUntil = Date.now() + 600
  window.scrollTo({
    top: window.scrollY + el.getBoundingClientRect().top - SCROLL_OFFSET,
    behavior: 'smooth',
  })
}

/** 取最后一个越过阈值线的锚点作为当前项（锚点按文档顺序返回） */
function onScroll() {
  if (spyFrame) return
  spyFrame = requestAnimationFrame(() => {
    spyFrame = 0
    if (Date.now() < suppressSpyUntil) return
    const threshold = SCROLL_OFFSET + 8
    let current = ''
    for (const el of document.querySelectorAll<HTMLElement>('[data-anchor]')) {
      if (el.getBoundingClientRect().top > threshold) break
      current = el.dataset.anchor ?? ''
    }
    activeKey.value = current || sections.value[0]?.key || ''
  })
}

/* ---------- 加载：先取 schema 构建表单，再取后端真实设置覆盖默认值 ---------- */
async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const spec = await fetchOpenApiSpec()
    const root = resolveNode(spec, { $ref: SETTINGS_REF })
    const entries = Object.entries(root.properties ?? {})
    if (!entries.length) throw new Error('OpenAPI 规范中未找到 AppSettings 定义')

    for (const key of Object.keys(model)) delete model[key]
    for (const [key, node] of entries) {
      model[key] = buildDefaultModel(spec, node) as Record<string, unknown>
    }
    doc.value = spec
    activeKey.value = entries[0]?.[0] ?? ''
    await loadSettings()
  } catch (err) {
    errorMsg.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

/** 拉取后端真实设置覆盖 schema 默认值（仅覆盖 schema 中已定义的字段） */
async function loadSettings() {
  settingsError.value = ''
  try {
    const data = await fetchSettings()
    for (const key of Object.keys(model)) {
      const target = model[key]
      const source = data[key]
      if (!target || !source || typeof source !== 'object') continue
      for (const [fieldKey, value] of Object.entries(source)) {
        if (fieldKey in target) target[fieldKey] = value
      }
    }
  } catch (err) {
    settingsError.value = err instanceof Error ? err.message : String(err)
  } finally {
    // 无论加载成功与否，当前表单内容即保存基线
    baseline.value = stableStringify(model)
  }
}

/** 保存：仅提交有改动的 section，成功后以当前内容为新基线 */
async function save() {
  const partial: AppSettingsPayload = {}
  for (const key of dirtyKeys.value) {
    const value = model[key]
    if (value) partial[key] = value
  }
  saving.value = true
  try {
    const updated = await updateSettings(partial)
    baseline.value = stableStringify(model)
    ElMessage.success(updated.length ? `已更新 ${updated.length} 项设置` : '设置已保存')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '保存设置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  void load()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  if (spyFrame) cancelAnimationFrame(spyFrame)
})
</script>

<style scoped>
.settings-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

.page-state {
  padding: 8px 0;
}

.error-detail {
  font-size: 12px;
  color: var(--color-text);
  opacity: 0.65;
  margin-bottom: 12px;
}

/* 左导航固定宽度并吸顶（避开 60px 固定导航栏），右内容自适应 */
.settings-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.nav-col {
  position: sticky;
  top: 84px;
}

.content-col {
  display: grid;
  gap: 20px;
  min-width: 0;
}

/* 卡片入场过渡 */
.section-card {
  animation: settings-fade-up 0.3s ease both;
}

@keyframes settings-fade-up {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

.settings-alert {
  margin-bottom: 0;
}

/* 保存栏吸底：长表单滚动时始终可保存 */
.settings-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 18px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: var(--shadow-lg);
}

.footer-hint {
  font-size: 12px;
  color: var(--color-text);
  opacity: 0.65;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 窄屏：导航不再侧置吸顶，改为整宽置于内容之上 */
@media (max-width: 1023px) {
  .settings-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .nav-col {
    position: static;
  }
}

@media (max-width: 767px) {
  .settings-page {
    padding: 20px 16px 32px;
  }
}
</style>
