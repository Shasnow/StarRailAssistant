<template>
  <section class="login-page" :style="{ '--login-bg': `url(${theme.backgrounds.hero})` }">
    <div class="login-card panel">
      <div class="login-hero">
        <img class="login-avatar" :src="theme.avatar" alt="" />
        <div>
          <p class="eyebrow">StarRailAssistant WebUI</p>
          <h1>远程控制台</h1>
          <p class="login-desc">输入在 SRA.exe 中设置的访问令牌后进入页面。</p>
        </div>
      </div>
      <p class="login-note">令牌不会在页面上明文展示，也不会预填默认值。</p>
      <el-input
        v-model="tokenDraft"
        class="login-input"
        type="password"
        show-password
        size="large"
        placeholder="请输入访问令牌"
        @keyup.enter="login"
      />
      <el-button :icon="Connection" type="primary" size="large" :loading="auth.checking" @click="login">
        进入 WebUI
      </el-button>
      <p v-if="auth.error" class="login-error">{{ auth.error }}</p>
    </div>
    <p class="login-quote">{{ greeting }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Connection } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import theme from '@/configs/theme'
import { randomGreeting } from '@/constants/greetings'

const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const tokenDraft = ref(auth.token)
const greeting = randomGreeting()

async function login() {
  try {
    await auth.login(tokenDraft.value)
    await app.refreshAll()
    router.push('/tasks')
  } catch {
    // Error is already set in auth store
  }
}
</script>
