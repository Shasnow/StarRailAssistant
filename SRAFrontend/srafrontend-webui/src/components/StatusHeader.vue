<template>
  <header class="topbar">
    <div class="brand">
      <img class="brand-avatar" :src="avatar" alt="" />
      <div>
        <p class="eyebrow">StarRailAssistant WebUI</p>
        <h1>远程控制台</h1>
      </div>
    </div>

    <div class="top-status">
      <el-tag round :type="healthTag" effect="light">
        <el-icon><Connection /></el-icon>
        {{ healthLabel }}
      </el-tag>
      <el-tag round :type="runningTag" effect="light">
        <el-icon><Monitor /></el-icon>
        {{ runningLabel }}
      </el-tag>
      <el-button text @click="$emit('logout')">退出</el-button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Connection, Monitor } from '@element-plus/icons-vue'

defineProps<{
  avatar: string
  healthLabel: string
  runningLabel: string
  healthTag: 'success' | 'danger'
  runningTag: 'success' | 'info'
}>()

defineEmits<{
  logout: []
}>()
</script>
