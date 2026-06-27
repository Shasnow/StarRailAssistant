<template>
  <nav :class="mobile ? 'mobile-bottom-nav' : 'page-nav'">
    <template v-if="mobile">
      <button v-for="item in items" :key="item.page" :class="{ active: activePage === item.page }" @click="$emit('switch', item.page)">
        {{ item.mobileLabel }}
      </button>
    </template>
    <template v-else>
      <el-button v-for="item in items" :key="item.page" :type="activePage === item.page ? 'primary' : 'default'" @click="$emit('switch', item.page)">
        {{ item.desktopLabel }}
      </el-button>
    </template>
  </nav>
</template>

<script setup lang="ts">
import type { PageKey } from '../types'

withDefaults(defineProps<{
  activePage: PageKey
  mobile?: boolean
}>(), {
  mobile: false
})

defineEmits<{
  switch: [page: PageKey]
}>()

const items: Array<{ page: PageKey; mobileLabel: string; desktopLabel: string }> = [
  { page: 'tasks', mobileLabel: '任务', desktopLabel: '任务控制' },
  { page: 'settings', mobileLabel: '设置', desktopLabel: '全局设置' },
  { page: 'extensions', mobileLabel: '拓展', desktopLabel: '拓展' },
  { page: 'logs', mobileLabel: '日志', desktopLabel: '日志' }
]
</script>

