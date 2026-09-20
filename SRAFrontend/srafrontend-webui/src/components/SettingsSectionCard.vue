<template>
  <!-- data-anchor 落在卡片根元素上（PanelCard 单根，属性透传），供导航滚动定位 -->
  <PanelCard :title="label" class="section-card" :data-anchor="sectionKey">
    <div class="section-fields">
      <template v-for="[key, node] in fields" :key="key">
        <!-- 数组 / 嵌套对象：整体作为一个分组渲染，头部显示 key 与描述 -->
        <div v-if="isGroup(node)" class="field-block">
          <div class="group-head">
            <div class="group-label">{{ key }}</div>
            <div v-if="descriptionOf(node)" class="group-desc" :title="descriptionOf(node)">
              {{ descriptionOf(node) }}
            </div>
          </div>
          <!-- 数组用条目编辑器（增删条目），嵌套对象走 SchemaForm 递归 -->
          <SchemaArrayEditor v-if="kindOf(node) === 'array'" :node="node" :doc="doc" :model-value="section[key]"
            @update:model-value="setField(key, $event)" />
          <SchemaForm v-else :schema="node" :doc="doc" :model-value="section[key]"
            @update:model-value="setField(key, $event)" />
        </div>

        <!-- 叶子字段：复用单字段控件（类型推断 + 实时校验） -->
        <div v-else class="field-cell">
          <SchemaField :field-key="key" :description="descriptionOf(node)" :node="node" :doc="doc"
            :model-value="section[key]" :dirty="isDirty(key)" @update:model-value="setField(key, $event)" />
        </div>
      </template>
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PanelCard from './PanelCard.vue'
import SchemaArrayEditor from './SchemaArrayEditor.vue'
import SchemaField from './SchemaField.vue'
import SchemaForm from './SchemaForm.vue'
import type { AppSettingsPayload } from '@/api/settings'
import type { OpenApiDocument, SchemaNode } from '@/utils/schemaForm'
import { fieldKind, resolveNode, stableStringify } from '@/utils/schemaForm'

// 单个设置分组：按 schema 逐字段渲染（分组根元素带 data-anchor，供左侧导航定位）
const props = defineProps<{
  /** 整个设置模型，本组件只读写自身 sectionKey 对应的分组 */
  model: AppSettingsPayload
  /** section key（如 advanced），同时作为分组锚点 */
  sectionKey: string
  /** 分组展示名 */
  label: string
  /** section 对应的 schema 节点（可能为 $ref） */
  node: SchemaNode
  doc: OpenApiDocument | null
  /** 基线快照：字段值与基线不一致时显示未保存圆点；undefined 表示不显示 */
  baseline?: Record<string, unknown>
}>()

/** 当前分组的值（模型未初始化时以空对象兜底，避免模板取值报错） */
const section = computed<Record<string, unknown>>(() => props.model[props.sectionKey] ?? {})

const resolved = computed(() => resolveNode(props.doc, props.node))
const fields = computed(() => Object.entries(resolved.value.properties ?? {}))

function isGroup(node: SchemaNode): boolean {
  const kind = fieldKind(resolveNode(props.doc, node))
  return kind === 'object' || kind === 'array'
}

function kindOf(node: SchemaNode): string {
  return fieldKind(resolveNode(props.doc, node))
}

/** description 优先取属性节点自身，$ref 目标上的说明作为兜底 */
function descriptionOf(node: SchemaNode): string {
  return node.description ?? resolveNode(props.doc, node).description ?? ''
}

function isDirty(key: string): boolean {
  if (props.baseline === undefined) return false
  return stableStringify(section.value[key]) !== stableStringify(props.baseline[key])
}

function setField(key: string, value: unknown) {
  const target = props.model[props.sectionKey]
  if (target) target[key] = value
}
</script>

<style scoped>
.section-fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px;
  align-items: start;
}

.field-cell {
  min-width: 0;
}

/* 数组 / 内联对象独占整行，虚线边框区分层级（与 SchemaForm 内样式保持一致） */
.field-block {
  grid-column: 1 / -1;
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px dashed var(--color-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-background-mute) 45%, transparent);
}

/* 分组头部：key 主标签 + description 辅助小字（样式对齐 SchemaField 的 field-titles） */
.group-head {
  display: grid;
  gap: 2px;
}

.group-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-heading);
}

.group-desc {
  font-size: 11px;
  color: var(--color-text);
  opacity: 0.55;
}
</style>
