<template>
  <PanelCard title="任务配置">
    <!-- 加载中 -->
    <div v-if="loading" class="panel-state">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- 加载失败：可重试 -->
    <div v-else-if="errorMsg" class="panel-state">
      <el-empty description="加载 OpenAPI 规范失败" :image-size="72">
        <div class="error-detail">{{ errorMsg }}</div>
        <el-button type="primary" @click="load">重试</el-button>
      </el-empty>
    </div>

    <!-- 标签页：TasksConfig 的每个子配置项一个标签页 -->
    <template v-else>
      <!-- 后端配置读取失败提示（不影响 schema 表单展示） -->
      <el-alert v-if="configsStore.detailError" class="detail-alert" type="error" :title="configsStore.detailError"
        :closable="false">
        <el-button size="small" @click="applyBackendValues">重试</el-button>
      </el-alert>

      <el-tabs v-model="activeTab" class="config-tabs">
        <el-tab-pane v-for="tab in tabs" :key="tab.key" :name="tab.key">
          <template #label>
            <span class="tab-label" :title="tab.key">{{ tab.label }}<span v-if="dirtyKeys.has(tab.key)"
                class="dirty-dot" title="有未保存的更改" /></span>
          </template>
          <div class="tab-pane-body">
            <SchemaForm :schema="tab.schema" :doc="doc" :model-value="configModel[tab.key]"
              :baseline="baselineModel ? baselineModel[tab.key] : undefined"
              @update:model-value="configModel[tab.key] = $event" />
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 保存：把当前表单内容 PUT 回 /api/Configs/{name} -->
      <div class="panel-footer">
        <span class="footer-hint">{{ isDirty ? '有未保存的更改' : configName ? `当前配置：${configName}` : '未选择配置' }}</span>
        <el-button type="primary" size="small"
          :disabled="!configName || !isDirty || !!configsStore.detailError || configsStore.detailLoading"
          :loading="configsStore.saving" @click="save">
          保存配置
        </el-button>
      </div>
    </template>
  </PanelCard>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { fetchOpenApiSpec } from '@/api/openapi'
import type { TasksConfigPayload } from '@/api/configs'
import { useConfigsStore } from '@/stores/configs'
import type { OpenApiDocument, SchemaNode } from '@/utils/schemaForm'
import { buildDefaultModel, resolveNode, stableStringify } from '@/utils/schemaForm'
import PanelCard from './PanelCard.vue'
import SchemaForm from './SchemaForm.vue'

const TASKS_CONFIG_REF = '#/components/schemas/TasksConfig'

const props = withDefaults(
  defineProps<{
    /** 排除的配置项 key（如 name / version），不渲染对应标签页 */
    excludeKeys?: string[]
    /** 当前选中的后端配置名；有值时加载真实配置覆盖默认值，并启用保存 */
    configName?: string
  }>(),
  { excludeKeys: () => [], configName: '' },
)

const configsStore = useConfigsStore()

const doc = ref<OpenApiDocument | null>(null)
const loading = ref(true)
const errorMsg = ref('')
const activeTab = ref('')

// 配置模型：按 schema 结构构建默认值，再由后端真实配置覆盖；字段值随表单实时写入
const configModel = reactive<TasksConfigPayload>({})

// 未保存更改检测：baseline 为最近一次加载/保存成功后的表单快照
const baseline = ref('')

const isDirty = computed(() => baseline.value !== '' && stableStringify(configModel) !== baseline.value)

/** 有未保存更改的顶层配置字段（key 集合），用于在标签页名称旁标记星号 */
const dirtyKeys = computed<Set<string>>(() => {
  if (!baseline.value) return new Set()
  const base = JSON.parse(baseline.value) as TasksConfigPayload
  const set = new Set<string>()
  for (const key of Object.keys(configModel)) {
    if (stableStringify(configModel[key]) !== stableStringify(base[key])) set.add(key)
  }
  return set
})

/** 基线快照的解析对象：下发给 SchemaForm 用于字段级未保存星号；无基线时为 null */
const baselineModel = computed(() =>
  baseline.value ? (JSON.parse(baseline.value) as TasksConfigPayload) : null,
)

/** 标签页列表：TasksConfig 的属性顺序即标签页顺序，跳过 excludeKeys 中的项 */
// label 优先取 schema 的 description（$ref 目标或属性节点上），无则回退原始 key
const tabs = computed<{ key: string; label: string; schema: SchemaNode }[]>(() => {
  const d = doc.value
  if (!d) return []
  const tasks = resolveNode(d, { $ref: TASKS_CONFIG_REF })
  return Object.entries(tasks.properties ?? {})
    .filter(([key]) => !props.excludeKeys.includes(key))
    .map(([key, node]) => {
      const schema = resolveNode(d, node)
      return {
        key,
        label: schema.description ?? node.description ?? key,
        schema,
      }
    })
})

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const spec = await fetchOpenApiSpec()
    doc.value = spec

    const tasks = resolveNode(spec, { $ref: TASKS_CONFIG_REF })
    for (const [key, node] of Object.entries(tasks.properties ?? {})) {
      if (props.excludeKeys.includes(key)) continue
      configModel[key] = buildDefaultModel(spec, node)
    }
    activeTab.value = tabs.value[0]?.key ?? ''
    await applyBackendValues()
  } catch (err) {
    errorMsg.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

/** 用后端真实配置覆盖表单默认值（仅覆盖模型中已有的顶层 key） */
async function applyBackendValues() {
  try {
    if (doc.value && props.configName) {
      const data = await configsStore.loadConfig(props.configName)
      if (!data) return
      for (const key of Object.keys(configModel)) {
        if (key in data) configModel[key] = data[key]
      }
    }
  } catch {
    // 读取失败已写入 configsStore.detailError，由模板中的 el-alert 展示
  } finally {
    // 无论加载成功与否，当前表单内容即保存基线
    baseline.value = stableStringify(configModel)
  }
}

// 切换选中配置时重新加载该配置的值
watch(() => props.configName, () => {
  if (doc.value) applyBackendValues()
})

/** 保存当前表单内容到后端（合并后端原始数据，保留 name/version 等未在表单中展示的字段） */
async function save(): Promise<boolean> {
  if (!props.configName) return false
  const payload = { ...configsStore.currentConfig, ...configModel }
  const ok = await configsStore.saveConfig(props.configName, payload)
  if (ok) {
    baseline.value = stableStringify(configModel)
    ElMessage.success('配置已保存')
  } else {
    ElMessage.error(configsStore.saveError || '保存失败')
  }
  return ok
}

onMounted(load)

// 供父组件（HomeView）在切换配置前检查未保存更改并触发保存
defineExpose({
  isDirty,
  save,
})
</script>

<style scoped>
.panel-state {
  padding: 8px 0;
}

.error-detail {
  font-size: 12px;
  color: var(--color-text);
  opacity: 0.65;
  margin-bottom: 12px;
}

.config-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.tab-label {
  font-size: 13px;
}

/* 未保存圆点：继承标签文字的前景色，避免与必填红色星号混淆 */
.dirty-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-left: 4px;
  border-radius: 50%;
  background: currentColor;
  vertical-align: middle;
}

.tab-pane-body {
  min-height: 160px;
}

.detail-alert {
  margin-bottom: 12px;
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.footer-hint {
  font-size: 12px;
  color: var(--color-text);
  opacity: 0.65;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
