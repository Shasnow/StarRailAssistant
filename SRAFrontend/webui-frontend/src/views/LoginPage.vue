<template>
  <section class="login-page">
    <div class="login-card panel">
      <img class="login-avatar" :src="avatar" alt="" />
      <p class="eyebrow">StarRailAssistant WebUI</p>
      <h1>远程控制台</h1>
      <p class="login-desc">请输入在 SRA.exe 设置中配置的 WebUI 访问令牌。</p>
      <el-input
        :model-value="token"
        class="login-input"
        type="password"
        show-password
        size="large"
        placeholder="请输入访问令牌"
        @update:model-value="$emit('update:token', String($event))"
        @keyup.enter="$emit('login')"
      />
      <el-button :icon="Connection" type="primary" size="large" :loading="checking" @click="$emit('login')">
        进入 WebUI
      </el-button>
      <p v-if="error" class="login-error">{{ error }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Connection } from '@element-plus/icons-vue'

defineProps<{
  avatar: string
  token: string
  checking: boolean
  error: string
}>()

defineEmits<{
  'update:token': [value: string]
  login: []
}>()
</script>

