import { defineStore } from 'pinia'
import { ref } from 'vue'
import { verifyToken } from '@/api/auth'
import { configureRequest } from '@/api/request'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sra-webui-token') ?? '')
  const isAuthed = ref(false)
  const checking = ref(false)
  const error = ref('')

  configureRequest({
    getToken: () => token.value,
    onUnauthorized: () => logout()
  })

  async function login(inputToken: string) {
    checking.value = true
    error.value = ''
    try {
      const trimmed = inputToken.trim()
      if (!trimmed) throw new Error('请输入访问令牌')
      await verifyToken(trimmed)
      token.value = trimmed
      localStorage.setItem('sra-webui-token', trimmed)
      isAuthed.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : '登录失败'
      throw e
    } finally {
      checking.value = false
    }
  }

  function logout() {
    localStorage.removeItem('sra-webui-token')
    token.value = ''
    isAuthed.value = false
  }

  async function verifyStoredToken() {
    if (!token.value) return false
    checking.value = true
    try {
      await verifyToken(token.value)
      isAuthed.value = true
      return true
    } catch {
      logout()
      return false
    } finally {
      checking.value = false
    }
  }

  return { token, isAuthed, checking, error, login, logout, verifyStoredToken }
})
