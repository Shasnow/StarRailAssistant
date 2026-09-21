<template>
  <div class="login-page">
    <!-- 背景大图 + 模糊：铺满全屏并放大 8%，避免模糊后边缘透出底色；
         后端背景接口不可用时回退到 .login-page 的兜底渐变 -->
    <img v-if="!bgFailed" class="login-bg" :src="siteConfig.bgUrl" alt="" aria-hidden="true" @error="bgFailed = true" />
    <div class="login-scrim" aria-hidden="true"></div>

    <section class="login-card" aria-labelledby="login-title">
      <header class="login-head">
        <img class="login-logo" :src="siteConfig.logo" alt="" />
        <h1 id="login-title" class="login-title">{{ siteConfig.title }}</h1>
        <p class="login-desc">该实例已启用访问认证，请输入 Access Token 继续</p>
      </header>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" hide-required-asterisk
        @submit.prevent="handleSubmit">
        <el-form-item label="Access Token" prop="token">
          <el-input v-model="form.token" type="password" size="large" show-password :prefix-icon="Key"
            placeholder="请输入 Access Token" autocomplete="current-password" :disabled="submitting" />
        </el-form-item>

        <p class="login-hint">请查看您的后端服务配置，获取 Access Token 后输入</p>

        <el-alert v-if="error" class="login-error" :title="error" type="error" show-icon :closable="false" />

        <el-button class="login-submit" type="primary" size="large" native-type="submit" :loading="submitting">
          {{ submitting ? '正在验证…' : '进入' }}
        </el-button>
      </el-form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Key } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import siteConfig from '@/configs/siteConfig'
import { verifyToken } from '@/api/auth'
import { setStoredToken } from '@/api/http'

const router = useRouter()
const route = useRoute()

const formRef = ref<FormInstance>()
const form = ref({ token: '' })
/** 提交中：按钮 loading、输入框禁用，防止重复提交 */
const submitting = ref(false)
/** 校验失败提示（401 或网络异常） */
const error = ref('')
const bgFailed = ref(false)

// 基本格式校验：必填、不含空白字符、长度上限
const rules: FormRules<typeof form> = {
  token: [
    { required: true, message: '请输入 access token', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        const token = (value ?? '').trim()
        if (!token) return callback(new Error('请输入 access token'))
        if (/\s/.test(token)) return callback(new Error('access token 不能包含空格'))
        if (token.length > 512) return callback(new Error('access token 长度不能超过 512 位'))
        callback()
      },
      trigger: 'blur',
    },
  ],
}

/** 登录成功后的目标地址：来自 401 跳转时写入的 redirect，仅接受站内路径 */
function redirectTarget(): string {
  const target = route.query.redirect
  if (typeof target === 'string' && target.startsWith('/') && !target.startsWith('//')) return target
  return '/'
}

/** 提交：表单校验通过后请求 /api/Auth 校验 token，成功则保存并进入主界面 */
async function handleSubmit() {
  if (submitting.value || !formRef.value) return
  error.value = ''

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const token = form.value.token.trim()
    await verifyToken(token)
    setStoredToken(token)
    ElMessage.success('验证通过')
    await router.replace(redirectTarget())
  } catch (err) {
    error.value = err instanceof Error ? err.message : '验证失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  min-height: 100svh;
  padding: 40px 20px;
  overflow: hidden;
  /* 背景图加载失败/加载中的兜底渐变（随主题色相低亮度着色，保证卡片层次） */
  background: linear-gradient(165deg,
      oklch(0.35 0.03 var(--hue)) 0%,
      oklch(0.24 0.03 var(--hue)) 55%,
      oklch(0.16 0.02 var(--hue)) 100%);
}

.login-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transform: scale(1.08);
  filter: blur(18px) saturate(1.15) brightness(0.9);
}

/* 压暗层：模糊背景之上再拉出中心与边缘的明暗差，突出居中的登录卡片 */
.login-scrim {
  position: absolute;
  inset: 0;
  background: radial-gradient(120% 90% at 50% 42%,
      rgb(0 0 0 / 16%) 0%,
      rgb(0 0 0 / 42%) 100%);
}

.login-card {
  position: relative;
  z-index: 1;
  width: min(420px, 100%);
  padding: 32px 32px 26px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: color-mix(in oklab, var(--color-surface) 92%, transparent);
  backdrop-filter: blur(14px) saturate(1.4);
  -webkit-backdrop-filter: blur(14px) saturate(1.4);
  box-shadow: var(--shadow-lg);
  animation: login-rise 0.35s ease both;
}

@keyframes login-rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

/* ---------- 头部 ---------- */
.login-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 22px;
  text-align: center;
}

.login-logo {
  width: 44px;
  height: 44px;
  margin-bottom: 2px;
}

.login-title {
  font-size: 21px;
  font-weight: 600;
  color: var(--color-heading);
  letter-spacing: 0.02em;
}

.login-desc {
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

/* ---------- 表单 ---------- */
.login-hint {
  margin: -4px 0 16px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-muted);
}

.login-error {
  margin-bottom: 16px;
}

.login-submit {
  width: 100%;
  letter-spacing: 0.06em;
}

/* 登录按钮与卡片同宽，移动端点击区域不小于 44px */
.login-submit:deep(span) {
  font-size: 15px;
}

/* ---------- 响应式 ---------- */
@media (max-width: 480px) {
  .login-page {
    padding: 24px 16px;
  }

  .login-card {
    padding: 26px 20px 20px;
    border-radius: 14px;
  }

  .login-logo {
    width: 38px;
    height: 38px;
  }

  .login-title {
    font-size: 19px;
  }

  /* 移动端降低模糊半径，减少大面积高斯模糊的渲染开销 */
  .login-bg {
    filter: blur(12px) saturate(1.1) brightness(0.9);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-card {
    animation: none;
  }
}
</style>