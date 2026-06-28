<template>
  <main class="app-shell">
    <AppAtmosphere />

    <LoginPage
      v-if="!auth.isAuthed"
      v-model:token="loginToken"
      :avatar="consoleAvatar"
      :checking="auth.checking"
      :error="auth.error"
      @login="login"
    />

    <template v-else>
      <StatusHeader
        :avatar="consoleAvatar"
        :health-label="app.healthLabel"
        :running-label="app.runningLabel"
        :health-tag="app.healthTag"
        :running-tag="app.runningTag"
        @logout="logout"
      />

      <PageNav />

      <router-view />
    </template>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import consoleAvatar from './assets/console-avatar.jpg'
import { useAuthStore } from './stores/auth'
import { useAppStore } from './stores/app'
import AppAtmosphere from './components/AppAtmosphere.vue'
import LoginPage from './views/LoginPage.vue'
import PageNav from './components/PageNav.vue'
import StatusHeader from './components/StatusHeader.vue'

const auth = useAuthStore()
const app = useAppStore()

const loginToken = ref(auth.token)

async function login() {
  try {
    await auth.login(loginToken.value)
    await app.refreshAll()
  } catch {
    // Error is already set in auth store
  }
}

function logout() {
  auth.logout()
  loginToken.value = ''
}

onMounted(async () => {
  const ok = await auth.verifyStoredToken()
  if (ok) {
    loginToken.value = auth.token
    await app.refreshAll()
  }
})
</script>
