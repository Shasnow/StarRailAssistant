import {defineStore} from 'pinia'
import {computed, reactive, ref} from 'vue'
import {ElMessage} from 'element-plus'
import {configureRequest} from '@/api/request'
import {auth} from '@/api/auth'
import * as configsApi from '@/api/configs'
import * as settingsApi from '@/api/settings'
import * as taskApi from '@/api/task'
import * as extensionsApi from '@/api/extensions'
import {createConfigModel, prepareConfigForSave} from '@/models/taskConfig'
import {createSettingsModel, prepareSettingsForSave} from '@/models/settings'
import type {SettingsModel, SraStatus, TaskConfig, TpTaskDefinition} from '@/types'

export const useAppStore = defineStore('app', () => {
  // Auth
  const token = ref(localStorage.getItem('sra-webui-token') ?? '')
  const isAuthed = ref(false)
  const checking = ref(false)
  const authError = ref('')

  configureRequest({
    getToken: () => token.value,
    onUnauthorized: () => logout()
  })

  async function login(inputToken: string) {
    checking.value = true
    authError.value = ''
    try {
      const trimmed = inputToken.trim()
      if (!trimmed) throw new Error('请输入访问令牌')
      await auth(trimmed)
      token.value = trimmed
      localStorage.setItem('sra-webui-token', trimmed)
      isAuthed.value = true
    } catch (e) {
      authError.value = e instanceof Error ? e.message : '登录失败'
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
      await auth(token.value)
      isAuthed.value = true
      return true
    } catch {
      logout()
      return false
    } finally {
      checking.value = false
    }
  }

  // Status
  const health = ref({ ok: false })
  const sraStatus = ref<SraStatus>({ running: false })
  const healthLabel = computed(() => (health.value.ok ? 'WebUI 在线' : 'WebUI 离线'))
  const healthTag = computed(() => (health.value.ok ? 'success' : 'danger'))
  const runningLabel = computed(() => (sraStatus.value.running ? '任务运行中' : '任务未运行'))
  const runningTag = computed(() => (sraStatus.value.running ? 'success' : 'info'))

  // Configs
  const configNames = ref<string[]>([])
  const selectedConfig = ref('')
  const configNameDraft = ref('')
  const configText = ref('')
  const configModel = ref<TaskConfig | null>(null)
  const startUsername = ref('')
  const startPassword = ref('')

  // Settings
  const settingsText = ref('')
  const settingsModel = ref<SettingsModel | null>(null)
  const settingsTab = ref('general')
  const emailAuthCodeDraft = ref('')

  // Task definitions
  const taskDefinitions = ref<TpTaskDefinition[]>([])
  const newPowerTask = reactive({
    taskIndex: 0,
    levelIndex: 0,
    count: 1,
    runtimes: 1,
    autoDetect: false
  })

  // Extensions
  const extensionState = reactive({
    autoPlotEnabled: false,
    skipPlot: false
  })

  // Logs
  const logs = ref<string[]>([])
  const logCount = ref(160)
  const streaming = ref(true)

  const rewardLabels = ['漫游签证', '派遣', '邮件', '每日实训', '无名勋礼', '巡星之礼', '兑换码']

  async function runAction(action: () => Promise<void>, success?: string) {
    try {
      await action()
      if (success) ElMessage.success(success)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '操作失败')
    }
  }

  async function loadStatus() {
    sraStatus.value = await taskApi.getHealth()
  }

  async function loadConfigs() {
    const payload = await configsApi.getConfigNames()
    configNames.value = payload
    if (!selectedConfig.value && payload.length) selectedConfig.value = payload[0]
  }

  async function loadConfigDetail() {
    if (!selectedConfig.value) return
    const payload = await configsApi.getConfigDetail(selectedConfig.value)
    const model = createConfigModel(payload, selectedConfig.value)
    configModel.value = model
    configText.value = JSON.stringify(model, null, 2)
    startUsername.value = ''
    startPassword.value = ''
  }

  async function loadMetadata() {
    const payload = await taskApi.getTaskDefinitions()
    taskDefinitions.value = payload
    if (!taskDefinitions.value.some((task) => task.index === newPowerTask.taskIndex))
      newPowerTask.taskIndex = taskDefinitions.value[0]?.index ?? 0
  }

  async function loadSettings() {
    const payload = await settingsApi.getSettings()
    settingsModel.value = createSettingsModel(payload)
    emailAuthCodeDraft.value = ''
    settingsText.value = JSON.stringify(settingsModel.value, null, 2)
  }

  async function loadLogs() {
    logs.value = await taskApi.getLogs(logCount.value)
  }

  async function refreshAll() {
    await Promise.allSettled([loadStatus(), loadConfigs(), loadSettings(), loadLogs(), loadMetadata()])
    if (selectedConfig.value) await loadConfigDetail()
  }

  async function saveConfig() {
    await runAction(async () => {
      if (!selectedConfig.value) throw new Error('请先选择配置')
      if (!configModel.value) throw new Error('当前配置尚未加载')
      const body = prepareConfigForSave(configModel.value, {
        username: startUsername.value,
        password: startPassword.value
      })
      await configsApi.saveConfig(selectedConfig.value, body)
      configText.value = JSON.stringify(body, null, 2)
      await Promise.allSettled([loadStatus(), loadLogs()])
    }, '配置已保存')
  }

  async function saveSettings() {
    await runAction(async () => {
      const source = settingsText.value || '{}'
      const body = JSON.parse(source)
      await settingsApi.saveSettings(body)
      settingsModel.value = createSettingsModel(body)
      settingsText.value = JSON.stringify(settingsModel.value, null, 2)
      await Promise.allSettled([loadStatus(), loadLogs()])
    }, '设置已保存')
  }

  async function saveSettingsGui() {
    await runAction(async () => {
      if (!settingsModel.value) throw new Error('设置尚未加载')
      const body = prepareSettingsForSave(settingsModel.value, emailAuthCodeDraft.value)
      await settingsApi.saveSettings(body)
      settingsText.value = JSON.stringify(body, null, 2)
      if (body.advanced?.['webui.remote.token'] && body.advanced['webui.remote.token'] !== token.value) {
        token.value = String(body.advanced['webui.remote.token'])
        localStorage.setItem('sra-webui-token', token.value)
      }
      await Promise.allSettled([loadStatus(), loadLogs()])
    }, '设置已保存')
  }

  async function createConfig() {
    await runAction(async () => {
      const name = configNameDraft.value.trim()
      if (!name) throw new Error('请输入配置名称')
      await configsApi.createConfig(name)
      selectedConfig.value = name
      configNameDraft.value = ''
      await loadConfigs()
      await loadConfigDetail()
    }, '配置已创建')
  }

  async function startTask() {
    await runAction(async () => {
      await taskApi.runTask(selectedConfig.value || null)
      await loadStatus()
    }, '任务已启动')
  }

  async function stopTask() {
    await runAction(async () => {
      await taskApi.stopTask()
      await new Promise(resolve => setTimeout(resolve, 200))
      await loadStatus()
    }, '已发送停止指令')
  }

  async function saveAutoPlot() {
    await runAction(async () => {
      await extensionsApi.saveAutoPlot(extensionState.autoPlotEnabled, extensionState.skipPlot)
      await loadLogs()
    }, '自动对话设置已应用')
  }

  async function runWarpForecast() {
    await runAction(async () => {
      if (!settingsModel.value) throw new Error('设置尚未加载')
      const body = prepareSettingsForSave(settingsModel.value, emailAuthCodeDraft.value)
      await settingsApi.saveSettings(body)
      settingsText.value = JSON.stringify(body, null, 2)
      await extensionsApi.runWarpForecast()
      await loadStatus()
    }, '抽卡资源预测已启动')
  }

  function syncJsonFromForm() {
    if (!configModel.value) return
    configText.value = JSON.stringify(prepareConfigForSave(configModel.value, {
      username: startUsername.value,
      password: startPassword.value
    }), null, 2)
    ElMessage.success('已从表单同步到 JSON')
  }

  function applyJsonToForm() {
    runAction(async () => {
      const parsed = JSON.parse(configText.value || '{}')
      configModel.value = createConfigModel(parsed, selectedConfig.value)
    }, 'JSON 已应用到表单')
  }

  function syncSettingsJsonFromForm() {
    if (!settingsModel.value) return
    settingsText.value = JSON.stringify(prepareSettingsForSave(settingsModel.value, emailAuthCodeDraft.value), null, 2)
    ElMessage.success('已从表单同步到 JSON')
  }

  function applySettingsJsonToForm() {
    runAction(async () => {
      const parsed = JSON.parse(settingsText.value || '{}')
      settingsModel.value = createSettingsModel(parsed)
    }, 'JSON 已应用到表单')
  }

  function updateGamePaths(value: string | number) {
    if (!settingsModel.value) return
    settingsModel.value.general['gamePath.uris'] = String(value)
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
  }

  return {
    // Auth
    token, isAuthed, checking, authError,
    login, logout, verifyStoredToken,
    // Status
    health, sraStatus, healthLabel, healthTag, runningLabel, runningTag,
    // Configs
    configNames, selectedConfig, configNameDraft, configText, configModel,
    startUsername, startPassword,
    // Settings
    settingsText, settingsModel, settingsTab, emailAuthCodeDraft,
    // Tasks
    taskDefinitions, newPowerTask, rewardLabels,
    // Extensions
    extensionState,
    // Logs
    logs, logCount, streaming,
    // Actions
    loadStatus, loadConfigs, loadConfigDetail, loadMetadata, loadSettings, loadLogs,
    refreshAll, saveConfig, saveSettings, saveSettingsGui, createConfig,
    startTask, stopTask, saveAutoPlot, runWarpForecast,
    syncJsonFromForm, applyJsonToForm, syncSettingsJsonFromForm, applySettingsJsonToForm,
    updateGamePaths
  }
})
