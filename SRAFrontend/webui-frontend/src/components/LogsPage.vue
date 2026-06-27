<template>
  <section :class="mobile ? 'mobile-card' : 'page-wrap'">
    <section :class="mobile ? '' : 'panel logs-panel logs-page-panel'">
      <div class="panel-title logs-title">
        <span>日志</span>
        <div class="log-tools">
          <el-input-number :model-value="count" :min="10" :max="1000" :step="10" controls-position="right" @update:model-value="$emit('update:count', Number($event))" />
          <el-switch :model-value="streaming" active-text="实时" inactive-text="关闭" @update:model-value="$emit('update:streaming', Boolean($event))" @change="$emit('toggle-stream', $event)" />
          <el-button :icon="Tickets" @click="$emit('refresh')">刷新</el-button>
        </div>
      </div>
      <el-scrollbar ref="scrollbar" :class="mobile ? 'log-scroll mobile-log-scroll' : 'log-scroll large'">
        <pre class="logs">{{ logs.join('\n') || '暂无日志' }}</pre>
      </el-scrollbar>
    </section>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ScrollbarInstance } from 'element-plus'
import { Tickets } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  logs: string[]
  count: number
  streaming: boolean
  mobile?: boolean
}>(), {
  mobile: false
})

const emit = defineEmits<{
  'update:count': [value: number]
  'update:streaming': [value: boolean]
  'toggle-stream': [value: string | number | boolean]
  refresh: []
  'scrollbar-ready': [scrollbar: ScrollbarInstance | undefined]
}>()

const scrollbar = ref<ScrollbarInstance>()

watch(scrollbar, (value) => emit('scrollbar-ready', value), { immediate: true })
</script>

