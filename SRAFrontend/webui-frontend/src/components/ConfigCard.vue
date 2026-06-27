<template>
  <section :class="mobile ? 'mobile-card' : 'panel config-card'">
    <div class="panel-title">
      <span>配置</span>
      <el-button :icon="Refresh" circle text @click="$emit('load-configs')" />
    </div>
    <el-select :model-value="selectedConfig" filterable class="full" placeholder="选择配置" @update:model-value="$emit('update:selectedConfig', String($event))" @change="$emit('load-detail')">
      <el-option v-for="item in configNames" :key="item" :label="item" :value="item" />
    </el-select>
    <div :class="mobile ? 'mobile-create-row' : 'create-row'">
      <el-input :model-value="draft" placeholder="新配置名称" clearable @update:model-value="$emit('update:draft', String($event))" />
      <el-button :icon="DocumentAdd" type="primary" plain @click="$emit('create')">创建</el-button>
    </div>
    <div :class="mobile ? 'mobile-action-grid' : 'quick-actions'">
      <el-button :icon="Check" type="primary" @click="$emit('save')">保存</el-button>
      <el-button :icon="DocumentChecked" @click="$emit('load-detail')">重载</el-button>
      <el-button v-if="!mobile" :icon="Operation" @click="$emit('open-settings')">全局设置</el-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Check, DocumentAdd, DocumentChecked, Operation, Refresh } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  configNames: string[]
  selectedConfig: string
  draft: string
  mobile?: boolean
}>(), {
  mobile: false
})

defineEmits<{
  'update:selectedConfig': [value: string]
  'update:draft': [value: string]
  'load-configs': []
  'load-detail': []
  create: []
  save: []
  'open-settings': []
}>()
</script>

