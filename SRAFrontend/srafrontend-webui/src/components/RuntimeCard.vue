<template>
  <section class="panel control-panel">
    <div class="panel-title">
      <span>运行</span>
      <el-button :icon="Refresh" circle text @click="$emit('refresh')" />
    </div>
    <div class="control-actions">
      <el-button :icon="VideoPlay" type="primary" size="large" @click="$emit('start')">启动任务</el-button>
      <el-button :icon="SwitchButton" type="danger" plain size="large" @click="$emit('stop')">停止</el-button>
    </div>
    <div class="status-list">
      <div>
        <span>PID</span>
        <strong>{{ status.pid ?? '-' }}</strong>
      </div>
      <div>
        <span>模式</span>
        <strong>{{ status.mode ?? '-' }}</strong>
      </div>
      <div>
        <span>配置</span>
        <strong>{{ status.configs }}</strong>
      </div>
      <div>
        <span>任务</span>
        <strong>{{ status.task }}</strong>
      </div>
      <div>
        <span>状态</span>
        <strong>{{ status.status==='running' ? '运行中' : '未运行' }}</strong>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Refresh, SwitchButton, VideoPlay } from '@element-plus/icons-vue'
import type { SraStatus } from '@/types'

defineProps<{
  status: SraStatus
  healthOk: boolean
}>()

defineEmits<{
  refresh: []
  start: []
  stop: []
}>()
</script>
