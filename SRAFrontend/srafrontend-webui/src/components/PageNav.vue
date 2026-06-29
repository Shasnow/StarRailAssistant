<template>
  <nav class="page-nav">
    <router-link
      v-for="item in items"
      :key="item.path"
      :to="item.path"
      custom
      v-slot="{ navigate, isActive }"
    >
      <button type="button" :class="{ active: isActive }" @click="navigate">
        <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { Document, Operation, Tickets, Link } from '@element-plus/icons-vue'

const items = [
  { path: '/tasks', label: '任务控制', icon: Document },
  { path: '/settings', label: '设置中心', icon: Operation },
  { path: '/extensions', label: '拓展中心', icon: Link },
  { path: '/logs', label: '运行日志', icon: Tickets }
]
</script>
