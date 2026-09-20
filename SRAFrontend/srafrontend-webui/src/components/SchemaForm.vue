<template>
  <!-- 对象 schema：渲染字段集合 -->
  <div v-if="isObject" class="schema-fields">
    <template v-for="[key, node] in fields" :key="key">
      <!-- 数组字段：条目编辑器（对象条目嵌套分组 / 基本类型行内控件，均可增删） -->
      <div v-if="kindOf(node) === 'array'" class="field-block">
        <SchemaArrayEditor :node="node" :doc="doc" :label="key" :description="node.description"
          :model-value="arrayModel(key)" :baseline="baselineItems(key)" @update:model-value="setField(key, $event)" />
      </div>

      <!-- 对象字段（$ref 解析后内联展开） -->
      <div v-else-if="kindOf(node) === 'object'" class="field-block">
        <div class="field-titles">
          <div class="block-label">{{ key }}</div>
          <div v-if="node.description" class="field-desc" :title="node.description">{{ node.description }}</div>
        </div>
        <SchemaForm :schema="node" :doc="doc" :model-value="recordValue()[key]" :baseline="baselineRecord()[key]"
          @update:model-value="setField(key, $event)" />
      </div>

      <!-- 叶子字段 -->
      <SchemaField v-else :field-key="key" :description="node.description" :node="node" :doc="doc"
        :model-value="recordValue()[key]" :dirty="isKeyDirty(key)" @update:model-value="setField(key, $event)" />
    </template>
  </div>

  <!-- 叶子 schema：name / version 这类标量标签页直接渲染单控件 -->
  <SchemaField v-else :field-key="fieldKey" :description="label ?? '值'" :node="schema" :doc="doc" :model-value="model"
    :dirty="isSelfDirty" @update:model-value="model = $event" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { OpenApiDocument, SchemaNode } from '@/utils/schemaForm'
import { fieldKind, resolveNode, stableStringify } from '@/utils/schemaForm'
import SchemaArrayEditor from './SchemaArrayEditor.vue'
import SchemaField from './SchemaField.vue'

// 递归 schema 表单：对象渲染字段集合，数组支持增删条目，$ref 由 resolveNode 解析
defineOptions({ name: 'SchemaForm' })

const props = defineProps<{
  schema: SchemaNode
  doc: OpenApiDocument | null
  label?: string
  fieldKey?: string
  /** 该层级对应的基线快照（最近一次加载/保存的值）；undefined 表示无基线，不显示未保存星号 */
  baseline?: unknown
}>()

const model = defineModel<unknown>({ required: true })

const resolved = computed(() => resolveNode(props.doc, props.schema))
const isObject = computed(() => fieldKind(resolved.value) === 'object')
const fields = computed(() => Object.entries(resolved.value.properties ?? {}))

function kindOf(node: SchemaNode) {
  return fieldKind(resolveNode(props.doc, node))
}

function recordValue(): Record<string, unknown> {
  return isObject.value ? ((model.value as Record<string, unknown>) ?? {}) : {}
}

// ---- 基线对比：与基线不一致的字段在 key 旁显示未保存星号 ----

function baselineRecord(): Record<string, unknown> {
  return props.baseline != null && typeof props.baseline === 'object' && !Array.isArray(props.baseline)
    ? (props.baseline as Record<string, unknown>)
    : {}
}

function baselineItems(key: string): unknown[] {
  const v = baselineRecord()[key]
  return Array.isArray(v) ? v : []
}

function isKeyDirty(key: string): boolean {
  if (props.baseline === undefined) return false
  return stableStringify(recordValue()[key]) !== stableStringify(baselineRecord()[key])
}

const isSelfDirty = computed(
  () => props.baseline !== undefined && stableStringify(model.value) !== stableStringify(props.baseline),
)

function arrayModel(key: string): unknown[] {
  const v = recordValue()[key]
  return Array.isArray(v) ? v : []
}

function setField(key: string, value: unknown) {
  recordValue()[key] = value
}
</script>

<style scoped>
.schema-fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px;
  align-items: start;
}

/* 数组/内联对象独占整行，虚线边框区分层级 */
.field-block {
  grid-column: 1 / -1;
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px dashed var(--color-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-background-mute) 45%, transparent);
}

.field-titles {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.block-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-heading);
}

.field-desc {
  font-size: 11px;
  color: var(--color-text);
  opacity: 0.55;
}
</style>
