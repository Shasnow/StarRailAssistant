<template>
  <main class="app-shell">
    <AppAtmosphere />

    <LoginPage
      v-if="!isAuthed"
      v-model:token="loginToken"
      :avatar="consoleAvatar"
      :checking="authChecking"
      :error="authError"
      @login="login"
    />

    <template v-else-if="isMobileUi">
      <section class="mobile-shell">
        <StatusHeader
          mobile
          :avatar="consoleAvatar"
          :health-label="health.ok ? 'WebUI 在线' : 'WebUI 离线'"
          :running-label="sraStatus.running ? '任务运行中' : '任务未运行'"
          :health-tag="healthTag"
          :running-tag="runningTag"
          @logout="logout"
        />

        <main class="mobile-content">
          <section v-if="activePage === 'tasks'" class="mobile-stack">
            <RuntimeCard mobile :status="sraStatus" :health-ok="health.ok" @refresh="refreshAll" @start="startTask" @stop="stopTask" />

            <ConfigCard
              mobile
              v-model:selected-config="selectedConfig"
              v-model:draft="configNameDraft"
              :config-names="configNames"
              @load-configs="loadConfigs"
              @load-detail="loadConfigDetail"
              @create="createConfig"
              @save="saveConfig"
            />

            <TaskEditor
              mobile
              v-model:task-tab="taskTab"
              v-model:config-text="configText"
              v-model:start-username="startUsername"
              v-model:start-password="startPassword"
              :config-model="configModel"
              :selected-config="selectedConfig"
              :task-definitions="taskDefinitions"
              :new-power-task="newPowerTask"
              :reward-labels="rewardLabels"
              @load-detail="loadConfigDetail"
              @save="saveConfig"
              @sync-json="syncJsonFromForm"
              @apply-json="applyJsonToForm"
            />
          </section>

          <SettingsPage
            v-else-if="activePage === 'settings'"
            mobile
            v-model:settings-tab="settingsTab"
            v-model:settings-text="settingsText"
            v-model:email-auth-code="emailAuthCodeDraft"
            :settings-model="settingsModel"
            @update-game-paths="updateGamePaths"
            @load="loadSettings"
            @save="saveSettingsGui"
            @sync-json="syncSettingsJsonFromForm"
            @apply-json="applySettingsJsonToForm"
          />

          <ExtensionsPage
            v-else-if="activePage === 'extensions'"
            mobile
            :settings-model="settingsModel"
            :extension-state="extensionState"
            @load-settings="loadSettings"
            @save-settings="saveSettingsGui"
            @save-auto-plot="saveAutoPlot"
            @run-warp-forecast="runWarpForecast"
          />

          <section v-else class="mobile-stack">
            <LogsPage
              mobile
              :logs="logs"
              v-model:count="logCount"
              v-model:streaming="streaming"
              @toggle-stream="toggleStream"
              @refresh="loadLogs"
              @scrollbar-ready="logScrollbar = $event"
            />
          </section>
        </main>

        <PageNav mobile :active-page="activePage" @switch="switchPage" />
      </section>
    </template>

    <template v-else>
    <StatusHeader
      :avatar="consoleAvatar"
      :health-label="healthLabel"
      :running-label="runningLabel"
      :health-tag="healthTag"
      :running-tag="runningTag"
      @logout="logout"
    />

    <PageNav :active-page="activePage" @switch="switchPage" />

    <section v-if="activePage === 'tasks'" class="workspace">
      <aside class="rail">
        <RuntimeCard :status="sraStatus" :health-ok="health.ok" @refresh="refreshAll" @start="startTask" @stop="stopTask" />

        <ConfigCard
          v-model:selected-config="selectedConfig"
          v-model:draft="configNameDraft"
          :config-names="configNames"
          @load-configs="loadConfigs"
          @load-detail="loadConfigDetail"
          @create="createConfig"
          @save="saveConfig"
          @open-settings="switchPage('settings')"
        />

        <section class="panel notes-panel">
          <div class="note-line">
            <span class="note-dot"></span>
            <span>启动任务需要 WebUI 以管理员权限运行。</span>
          </div>
          <div class="note-line">
            <span class="note-dot blush"></span>
            <span>清体力清单使用 SRA 内部副本定义。</span>
          </div>
        </section>
      </aside>

      <section class="main-grid">
        <TaskEditor
          v-model:task-tab="taskTab"
          v-model:config-text="configText"
          v-model:start-username="startUsername"
          v-model:start-password="startPassword"
          :config-model="configModel"
          :selected-config="selectedConfig"
          :task-definitions="taskDefinitions"
          :new-power-task="newPowerTask"
          :reward-labels="rewardLabels"
          @load-detail="loadConfigDetail"
          @save="saveConfig"
          @sync-json="syncJsonFromForm"
          @apply-json="applyJsonToForm"
        />
      </section>
    </section>

    <SettingsPage
      v-else-if="activePage === 'settings'"
      v-model:settings-tab="settingsTab"
      v-model:settings-text="settingsText"
      v-model:email-auth-code="emailAuthCodeDraft"
      :settings-model="settingsModel"
      @update-game-paths="updateGamePaths"
      @load="loadSettings"
      @save="saveSettingsGui"
      @sync-json="syncSettingsJsonFromForm"
      @apply-json="applySettingsJsonToForm"
    />

    <ExtensionsPage
      v-else-if="activePage === 'extensions'"
      :settings-model="settingsModel"
      :extension-state="extensionState"
      @load-settings="loadSettings"
      @save-settings="saveSettingsGui"
      @save-auto-plot="saveAutoPlot"
      @run-warp-forecast="runWarpForecast"
    />

    <LogsPage
      v-else
      :logs="logs"
      v-model:count="logCount"
      v-model:streaming="streaming"
      @toggle-stream="toggleStream"
      @refresh="loadLogs"
      @scrollbar-ready="logScrollbar = $event"
    />
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { ScrollbarInstance } from 'element-plus'
import { ElMessage } from 'element-plus'
import consoleAvatar from './assets/console-avatar.jpg'
import { apiRequest, verifyToken } from './api/client'
import AppAtmosphere from './components/AppAtmosphere.vue'
import ConfigCard from './components/ConfigCard.vue'
import ExtensionsPage from './components/ExtensionsPage.vue'
import LoginPage from './components/LoginPage.vue'
import LogsPage from './components/LogsPage.vue'
import PageNav from './components/PageNav.vue'
import RuntimeCard from './components/RuntimeCard.vue'
import StatusHeader from './components/StatusHeader.vue'
import SettingsPage from './components/SettingsPage.vue'
import TaskEditor from './components/TaskEditor.vue'
import { useLogStream } from './composables/useLogStream'
import { useMobileUi } from './composables/useMobileUi'
import { createConfigModel, prepareConfigForSave } from './models/taskConfig'
import { createSettingsModel, prepareSettingsForSave } from './models/settings'
import type { PageKey, SettingsModel, SraStatus, TaskConfig, TpTaskDefinition } from './types'

// App.vue is the orchestration layer for the WebUI shell.  Domain-shaped form
// logic lives in child components and model helpers, while this file keeps the
// shared state that must survive page switches: auth, selected config, runtime
// status, logs, and settings drafts.
const rewardLabels = ['漫游签证', '派遣', '邮件', '每日实训', '无名勋礼', '巡星之礼', '兑换码']

// Desktop and mobile layouts render different component arrangements, but they
// intentionally bind to the same refs.  This keeps phone browsers feature-parity
// with the desktop WebUI without maintaining a second API client.
const health = ref({ ok: false })
const sraStatus = ref<SraStatus>({ running: false })
const authToken = ref(localStorage.getItem('sra-webui-token') ?? '')
const loginToken = ref(authToken.value)
const isAuthed = ref(false)
const authChecking = ref(false)
const authError = ref('')
const activePage = ref<PageKey>('tasks')
const { isMobileUi } = useMobileUi()
const configNames = ref<string[]>([])
const selectedConfig = ref('')
const configNameDraft = ref('')
const configText = ref('')
const configModel = ref<TaskConfig | null>(null)
const settingsText = ref('')
const settingsModel = ref<SettingsModel | null>(null)
const settingsTab = ref('general')
const taskTab = ref('start')
const logs = ref<string[]>([])
const logCount = ref(160)
const streaming = ref(true)
const logScrollbar = ref<ScrollbarInstance>()
const startUsername = ref('')
const startPassword = ref('')
const emailAuthCodeDraft = ref('')
const taskDefinitions = ref<TpTaskDefinition[]>([])
const newPowerTask = reactive({
  taskIndex: 0,
  levelIndex: 0,
  count: 1,
  runtimes: 1,
  autoDetect: false
})
const extensionState = reactive({
  autoPlotEnabled: false,
  skipPlot: false
})

const {
  closeStream,
  scrollLogsToBottom,
  toggleStream: toggleLogStream
} = useLogStream(logs, authToken, logScrollbar)

const healthLabel = computed(() => (health.value.ok ? 'WebUI 在线' : 'WebUI 离线'))
const healthTag = computed(() => (health.value.ok ? 'success' : 'danger'))
const runningLabel = computed(() => (sraStatus.value.running ? '任务运行中' : '任务未运行'))
const runningTag = computed(() => (sraStatus.value.running ? 'success' : 'info'))
async function api<T>(url: string, init?: RequestInit): Promise<T> {
  // A 401 from any endpoint means the server token changed or local storage is
  // stale; returning to the login screen is clearer than retrying silently.
  return apiRequest<T>(url, authToken.value, () => {
    isAuthed.value = false
  }, init)
}

async function login() {
  authChecking.value = true
  authError.value = ''
  try {
    const token = loginToken.value.trim()
    if (!token) throw new Error('请输入访问令牌')
    await verifyToken(token)
    authToken.value = token
    localStorage.setItem('sra-webui-token', token)
    isAuthed.value = true
    await refreshAll()
    toggleStream(streaming.value)
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '登录失败'
  } finally {
    authChecking.value = false
  }
}

function logout() {
  closeStream()
  localStorage.removeItem('sra-webui-token')
  authToken.value = ''
  loginToken.value = ''
  isAuthed.value = false
}

async function switchPage(page: PageKey) {
  activePage.value = page
  if (page === 'settings' || page === 'extensions') await loadSettings()
  if (page === 'logs') await loadLogs()
}

async function runAction(action: () => Promise<void>, success?: string) {
  try {
    await action()
    if (success) ElMessage.success(success)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  }
}

async function refreshAll() {
  // Refresh independent resources in parallel so opening the WebUI on a phone
  // feels responsive even when logs/config files are large.
  await Promise.allSettled([loadStatus(), loadConfigs(), loadLogs(), loadMetadata()])
  if (selectedConfig.value) await loadConfigDetail()
}

async function loadMetadata() {
  // The trailblaze-power task list is backend metadata, not hard-coded UI text.
  // This preserves SRA's internal task definitions for both desktop and WebUI.
  const payload = await api<TpTaskDefinition[]>('/Metadata/trailblaze-power/tasks')
  taskDefinitions.value = payload
  if (!taskDefinitions.value.some((task) => task.index === newPowerTask.taskIndex))
    newPowerTask.taskIndex = taskDefinitions.value[0]?.index ?? 0
}

async function loadStatus() {
  const payload = await api<{ ok: boolean; sra?: SraStatus }>('/api/health')
  health.value.ok = payload.ok
  if (payload.sra) sraStatus.value = payload.sra
}

async function loadConfigs() {
  const payload = await api<string[]>('/Configs')
  configNames.value = payload
  if (!selectedConfig.value && payload.length) selectedConfig.value = payload[0]
}

async function loadConfigDetail() {
  if (!selectedConfig.value) return
  const payload = await api<unknown>(`/Configs/${encodeURIComponent(selectedConfig.value)}`)
  const model = createConfigModel(payload, selectedConfig.value)
  configModel.value = model
  // Keep a JSON escape hatch beside the GUI form.  The form covers common SRA
  // settings, while JSON still lets advanced users inspect the exact payload.
  configText.value = JSON.stringify(model, null, 2)
  startUsername.value = ''
  startPassword.value = ''
}

async function saveConfig() {
  await runAction(async () => {
    if (!selectedConfig.value) throw new Error('请先选择配置')
    if (!configModel.value) throw new Error('当前配置尚未加载')
    const body = prepareConfigForSave(configModel.value, {
      username: startUsername.value,
      password: startPassword.value
    })
    await api(`/Configs/${encodeURIComponent(selectedConfig.value)}`, {
      method: 'PUT',
      body: JSON.stringify(body)
    })
    configText.value = JSON.stringify(body, null, 2)
    await Promise.allSettled([loadStatus(), loadLogs()])
  }, '配置已保存')
}

async function loadSettings() {
  const payload = await api<SettingsModel>('/Settings')
  settingsModel.value = createSettingsModel(payload)
  emailAuthCodeDraft.value = ''
  settingsText.value = JSON.stringify(settingsModel.value, null, 2)
}

async function saveSettings() {
  await runAction(async () => {
    const source = settingsText.value || '{}'
    const body = JSON.parse(source)
    await persistSettings(body)
    settingsModel.value = createSettingsModel(body)
    settingsText.value = JSON.stringify(settingsModel.value, null, 2)
    await Promise.allSettled([loadStatus(), loadLogs()])
  }, '设置已保存')
}

async function saveSettingsGui() {
  await runAction(async () => {
    if (!settingsModel.value) throw new Error('设置尚未加载')
    const body = prepareSettingsForSave(settingsModel.value, emailAuthCodeDraft.value)
    await persistSettings(body)
    settingsText.value = JSON.stringify(body, null, 2)
    // If the user changes the WebUI token from inside WebUI, update the current
    // browser session immediately so the next request does not log them out.
    if (body.advanced?.['webui.remote.token'] && body.advanced['webui.remote.token'] !== authToken.value) {
      authToken.value = String(body.advanced['webui.remote.token'])
      loginToken.value = authToken.value
      localStorage.setItem('sra-webui-token', authToken.value)
    }
    await Promise.allSettled([loadStatus(), loadLogs()])
  }, '设置已保存')
}

async function persistSettings(body: SettingsModel) {
  await api('/Settings', {
    method: 'PUT',
    body: JSON.stringify(body)
  })
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
  // Element Plus textarea values arrive as a string, but the SRA setting is an
  // array.  Normalize here so the settings form and raw JSON stay equivalent.
  settingsModel.value.general['gamePath.uris'] = String(value)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
}

async function saveAutoPlot() {
  await runAction(async () => {
    await api('/Extensions/auto-plot', {
      method: 'POST',
      body: JSON.stringify({
        enabled: extensionState.autoPlotEnabled,
        skipPlot: extensionState.skipPlot
      })
    })
    await loadLogs()
  }, '自动对话设置已应用')
}

async function runWarpForecast() {
  await runAction(async () => {
    if (!settingsModel.value) throw new Error('设置尚未加载')
    const body = prepareSettingsForSave(settingsModel.value, emailAuthCodeDraft.value)
    await persistSettings(body)
    settingsText.value = JSON.stringify(body, null, 2)
    await api('/Extensions/warp-forecast/run', {
      method: 'POST',
      body: '{}'
    })
    await loadStatus()
  }, '抽卡资源预测已启动')
}

async function startTask() {
  await runAction(async () => {
    // The server starts/controls SRA-cli.  WebUI only sends the selected config
    // name so the backend behavior matches the desktop frontend path.
    await api('/Task/run', {
      method: 'POST',
      body: JSON.stringify({ configName: selectedConfig.value || null })
    })
    await loadStatus()
  }, '任务已启动')
}

async function stopTask() {
  await runAction(async () => {
    await api('/Task/stop', {
      method: 'POST',
      body: '{}'
    })
    await loadStatus()
  }, '已发送停止指令')
}

async function loadLogs() {
  const payload = await api<string[]>('/Task/logs?count=' + logCount.value)
  logs.value = payload
  await scrollLogsToBottom()
}

async function createConfig() {
  await runAction(async () => {
    const name = configNameDraft.value.trim()
    if (!name) throw new Error('请输入配置名称')
    await api(`/Configs/${encodeURIComponent(name)}`, { method: 'POST' })
    selectedConfig.value = name
    configNameDraft.value = ''
    await loadConfigs()
    await loadConfigDetail()
  }, '配置已创建')
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

function toggleStream(enabled: string | number | boolean) {
  toggleLogStream(enabled, () => {
    streaming.value = false
  })
}

onMounted(async () => {
  if (!authToken.value) return

  authChecking.value = true
  try {
    // Stored tokens are verified before rendering the control surface; this
    // avoids briefly exposing stale state after the server token is changed.
    await verifyToken(authToken.value)
    isAuthed.value = true
    loginToken.value = authToken.value
    await refreshAll()
    toggleStream(streaming.value)
  } catch {
    localStorage.removeItem('sra-webui-token')
    authToken.value = ''
    loginToken.value = ''
    isAuthed.value = false
  } finally {
    authChecking.value = false
  }
})
</script>
