<template>
  <!-- 对象 schema：渲染字段集合；带点号前缀的字段按第一段前缀归组（如 game.x → Game 组） -->
  <div v-if="isObject" class="schema-fields">
    <template v-for="section in sections" :key="section.prefix ?? '__flat__'">
      <div :class="section.prefix === null ? 'field-group-flat' : 'field-group'">
        <!-- 组标题条：仅前缀分组渲染，平铺字段无标题 -->
        <div v-if="section.prefix !== null" class="field-group-head">
          <span class="field-group-title">{{ groupTitle(section.prefix) }}</span>
          <span class="field-group-count">{{ section.fields.length }} 项</span>
        </div>

        <template v-for="[key, node] in section.fields" :key="key">
          <!-- 数组字段：条目编辑器（对象条目嵌套分组 / 基本类型行内控件，均可增删） -->
          <div v-if="kindOf(node) === 'array'" class="field-block">
            <SchemaArrayEditor :node="node" :doc="doc" :label="displayKey(key, section.prefix)"
              :description="node.description" :model-value="arrayModel(key)" :baseline="baselineItems(key)"
              @update:model-value="setField(key, $event)" />
          </div>

          <!-- 对象字段（$ref 解析后内联展开） -->
          <div v-else-if="kindOf(node) === 'object'" class="field-block">
            <div class="field-titles">
              <div class="block-label">{{ displayKey(key, section.prefix) }}</div>
              <div v-if="node.description" class="field-desc" :title="node.description">{{ node.description }}</div>
            </div>
            <SchemaForm :schema="node" :doc="doc" :model-value="recordValue()[key]" :baseline="baselineRecord()[key]"
              @update:model-value="setField(key, $event)" />
          </div>

          <!-- 叶子字段：组内显示时去掉前缀，写入模型仍用完整键名 -->
          <SchemaField v-else :field-key="displayKey(key, section.prefix)" :description="node.description" :node="node"
            :doc="doc" :model-value="recordValue()[key]" :dirty="isKeyDirty(key)"
            @update:model-value="setField(key, $event)" />
        </template>
      </div>
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

// ---- 前缀分组：按字段名第一段点号前缀归组（仅处理一层，如 game.server.id 归入 Game）----

interface FieldSection {
  /** 组前缀；null 表示无点号、不参与分组的平铺字段 */
  prefix: string | null
  fields: [string, SchemaNode][]
}

// 单次遍历完成分组：平铺字段在前，各组按首次出现顺序排列；computed 缓存保证不重复计算
const sections = computed<FieldSection[]>(() => {
  const flat: [string, SchemaNode][] = []
  const groups = new Map<string, [string, SchemaNode][]>()
  for (const entry of fields.value) {
    const dot = entry[0].indexOf('.')
    if (dot <= 0) {
      flat.push(entry)
      continue
    }
    const prefix = entry[0].slice(0, dot)
    const bucket = groups.get(prefix)
    if (bucket) bucket.push(entry)
    else groups.set(prefix, [entry])
  }
  return [{ prefix: null, fields: flat }, ...Array.from(groups, ([prefix, fs]) => ({ prefix, fields: fs }))]
})

// 组标题：前缀首字母大写（game → Game）
function groupTitle(prefix: string): string {
  return prefix.charAt(0).toUpperCase() + prefix.slice(1)
}

// 组内字段显示名：去掉组前缀（"game.channel" → "channel"），写入模型仍用完整键名
function displayKey(key: string, prefix: string | null): string {
  return prefix === null ? key : key.slice(prefix.length + 1)
}

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

/* 点号前缀分组：实线边框 + 标题条；组容器自身即字段网格（列宽与外层一致），与虚线块区分层级 */
.field-group {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px;
  align-items: start;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-background-mute) 25%, transparent);
}

.field-group-head {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--color-border);
}

.field-group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-heading);
}

.field-group-count {
  font-size: 11px;
  color: var(--color-text);
  opacity: 0.55;
}

/* 平铺字段外层容器透明化，子项直接参与 .schema-fields 的网格布局 */
.field-group-flat {
  display: contents;
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
