<template>
  <div class="field-cell">
    <div v-if="fieldKey || description" class="field-titles">
      <!-- 字段 key 总是作为主标签显示，方便对应后端配置字段；有未保存更改时在 key 旁标记圆点 -->
      <div v-if="fieldKey" class="field-label">
        {{ fieldKey }}<span v-if="dirty" class="dirty-dot" :title="t('common.unsaved')" />
      </div>
      <!-- description 作为辅助说明，以小字显示在 key 下方；截断时悬停 title 显示全文 -->
      <div v-if="description" class="field-desc" :title="descText">{{ descText }}</div>
    </div>

    <el-switch v-if="kind === 'boolean'" :model-value="boolVal" @update:model-value="onUpdate" />
    <el-select v-else-if="kind === 'enum'" class="control-full" :model-value="modelValue" @update:model-value="onUpdate">
      <el-option v-for="choice in enumChoices" :key="String(choice.value)" :label="choice.label" :value="choice.value" />
    </el-select>
    <el-input-number v-else-if="kind === 'integer' && !intTextInput" class="control-full" :model-value="numVal"
      :precision="0" :step="1" @update:model-value="onUpdate" />
    <!-- [integer, string] 联合类型：文本框 + 正则实时校验 -->
    <el-input v-else :model-value="textVal" clearable :inputmode="intTextInput ? 'numeric' : undefined"
      @update:model-value="onUpdate" />

    <div v-if="error" class="field-error" role="alert">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { i18n } from '@/locales'

import { computed, ref } from 'vue'
import type { OpenApiDocument, SchemaNode } from '@/utils/schemaForm'
import { fieldKind, isIntTextInput, localizedDescription, resolveNode, validateValue } from '@/utils/schemaForm'

const { t } = useI18n()

// 单字段渲染：按 schema 类型选择控件，输入时实时校验并显示错误
const props = defineProps<{
  node: SchemaNode
  modelValue?: unknown
  /** 字段 key，作为主标签显示 */
  fieldKey?: string
  /** schema description，辅助说明小字 */
  description?: string
  /** 与基线（最近一次加载/保存值）不一致，显示未保存星号 */
  dirty?: boolean
  doc?: OpenApiDocument | null
}>()

const emit = defineEmits<{ 'update:modelValue': [value: unknown] }>()

const resolved = computed(() => resolveNode(props.doc ?? null, props.node))
const kind = computed(() => fieldKind(resolved.value))
const intTextInput = computed(() => isIntTextInput(resolved.value))
// 枚举选项：值仍用 enum，标签优先 x-enum-labels[当前语言]，回退中文标签或原值
const enumChoices = computed(() => {
  const node = resolved.value
  const values = node.enum ?? []
  const rawLabels = node['x-enum-labels']
  const labels = Array.isArray(rawLabels)
    ? rawLabels
    : (rawLabels?.[i18n.global.locale.value] ?? rawLabels?.['zh-CN'] ?? [])
  return values.map((value, index) => ({
    value,
    label: labels[index] ?? String(value),
  }))
})
// 说明文字：优先 schema 的 x-i18n，回退到 description
const descText = computed(() => localizedDescription(resolved.value, props.description))

const error = ref<string | null>(null)

const boolVal = computed(() => props.modelValue === true)
const textVal = computed(() => (props.modelValue == null ? '' : String(props.modelValue)))
const numVal = computed(() => (typeof props.modelValue === 'number' ? props.modelValue : undefined))

function onUpdate(value: unknown) {
  error.value = validateValue(resolved.value, value)
  emit('update:modelValue', value)
}
</script>

<style scoped>
.field-cell {
  display: grid;
  gap: 6px;
  align-content: start;
  min-width: 0;
}

.field-titles {
  display: grid;
  gap: 2px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-heading);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
}

/* 未保存圆点：继承 key 的前景色，避免与必填红色星号混淆 */
.dirty-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-left: 4px;
  border-radius: 50%;
  background: currentColor;
  vertical-align: middle;
}

.field-desc {
  font-size: 11px;
  color: var(--color-text);
  opacity: 0.55;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
}

.control-full {
  width: 100%;
}

.field-error {
  font-size: 12px;
  color: #ef4444;
}
</style>
