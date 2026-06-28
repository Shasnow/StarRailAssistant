<template>
  <section class="login-page" :style="{ '--login-bg': `url(${loginBackground})` }">
    <div class="login-card panel">
      <div class="login-hero">
        <img class="login-avatar" :src="avatar" alt="" />
        <div>
          <p class="eyebrow">StarRailAssistant WebUI</p>
          <h1>远程控制台</h1>
          <p class="login-desc">输入在 SRA.exe 中设置的访问令牌后进入页面。</p>
        </div>
      </div>
      <p class="login-note">令牌不会在页面上明文展示，也不会预填默认值。</p>
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
    <p class="login-quote">{{ greeting }}</p>
  </section>
</template>

<script setup lang="ts">
import { Connection } from '@element-plus/icons-vue'
import loginBackground from '@/assets/bg-login.jpg'
import { randomGreeting } from '@/constants/greetings'

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

const greeting = randomGreeting()
</script>

