<template>
  <section class="page-wrap">
    <section class="panel logs-panel logs-page-panel">
      <div class="panel-title logs-title">
        <span>日志</span>
        <div class="log-tools">
          <el-input-number v-model="app.logCount" :min="10" :max="1000" :step="10" controls-position="right" />
          <el-switch v-model="app.streaming" active-text="实时" inactive-text="关闭" @change="toggleStream" />
          <el-button :icon="Tickets" @click="app.loadLogs()">刷新</el-button>
        </div>
      </div>
      <el-scrollbar ref="scrollbar" class="log-scroll large">
        <pre class="logs">{{ app.logs.join('\n') || '暂无日志' }}</pre>
      </el-scrollbar>
    </section>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { ScrollbarInstance } from 'element-plus'
import { Tickets } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { baseURL } from '@/api/request'

const app = useAppStore()
const scrollbar = ref<ScrollbarInstance>()

let eventSource: EventSource | null = null

async function scrollLogsToBottom() {
  await nextTick()
  scrollbar.value?.setScrollTop(999999)
}

function closeStream() {
  eventSource?.close()
  eventSource = null
}

function toggleStream() {
  closeStream()
  if (!app.streaming) return

  eventSource = new EventSource(`${baseURL}/Task/logs/stream?access_token=` + encodeURIComponent(app.token))
  eventSource.onmessage = async (event) => {
    app.logs.push(event.data)
    if (app.logs.length > 600) app.logs.splice(0, app.logs.length - 600)
    await scrollLogsToBottom()
  }
  eventSource.onerror = () => {
    app.streaming = false
    closeStream()
  }
}

watch(() => app.logs, () => scrollLogsToBottom(), { deep: true })

onMounted(async () => {
  await app.loadLogs()
  if (app.streaming) toggleStream()
})

onUnmounted(closeStream)
</script>
