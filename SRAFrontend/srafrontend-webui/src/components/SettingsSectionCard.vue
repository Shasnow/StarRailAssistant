<template>
  <!-- data-anchor 落在卡片根元素上（PanelCard 单根，属性透传），供导航滚动定位 -->
  <PanelCard :title="label" class="section-card" :data-anchor="sectionKey">
    <!-- 字段渲染整体委托 SchemaForm：点号前缀自动分组，数组/嵌套对象/叶子字段与未保存圆点统一处理 -->
    <SchemaForm :schema="node" :doc="doc" :model-value="section" :baseline="baseline" />
  </PanelCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PanelCard from './PanelCard.vue'
import SchemaForm from './SchemaForm.vue'
import type { AppSettingsPayload } from '@/api/settings'
import type { OpenApiDocument, SchemaNode } from '@/utils/schemaForm'

// 单个设置分组卡片：字段渲染委托 SchemaForm（含点号前缀分组、数组条目编辑、嵌套对象递归）
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
</script>
