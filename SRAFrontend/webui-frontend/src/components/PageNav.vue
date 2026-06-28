<template>
  <nav class="page-nav">
    <router-link
      v-for="item in items"
      :key="item.path"
      :to="item.path"
      custom
      v-slot="{ navigate, isActive }"
    >
      <el-button :type="isActive ? 'primary' : 'default'" @click="navigate">
        {{ item.label }}
      </el-button>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
const items = [
  { path: '/tasks', label: '任务控制' },
  { path: '/settings', label: '全局设置' },
  { path: '/extensions', label: '拓展' },
  { path: '/logs', label: '日志' }
]
</script>
