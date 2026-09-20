import { useIntervalFn } from '@vueuse/core'
import { computed, ref } from 'vue'
import { fetchTaskStatus, IDLE_TASK_STATUS, runTask, stopTask, type TaskStatus } from '@/api/task'

/** 状态轮询间隔（ms） */
const POLL_INTERVAL = 1000

/**
 * 任务运行控制：启动 / 停止 / 状态轮询。
 * - 启动成功后开启 1s 轮询，状态回到非 running 自动停止轮询
 * - 页面加载时调用 refresh() 同步后端状态（后端已在运行则恢复轮询）
 * - start/stop 失败时抛出 ApiError，由调用方展示；状态轮询单次失败静默忽略
 */
export function useTaskRunner() {
  const status = ref<TaskStatus>({ ...IDLE_TASK_STATUS })
  /** start / stop 请求进行中（供按钮禁用防重复提交） */
  const busy = ref(false)
  const isRunning = computed(() => status.value.status === 'running')

  /** 轮询防重入：上一次请求未返回时跳过本轮 */
  let polling = false

  async function poll(): Promise<void> {
    if (polling) return
    polling = true
    try {
      const next = await fetchTaskStatus()
      status.value = next
      // 任务结束后自动停止轮询
      if (next.status !== 'running') pausePolling()
    } catch {
      // 单次轮询失败忽略（网络抖动 / 后端短暂不可用），保留上次状态
    } finally {
      polling = false
    }
  }

  const {
    pause: pausePolling,
    resume: resumePolling,
    isActive: pollActive,
  } = useIntervalFn(poll, POLL_INTERVAL, { immediate: false })

  /** 拉取一次状态；发现任务在运行则确保轮询开启 */
  async function refresh(): Promise<void> {
    try {
      status.value = await fetchTaskStatus()
    } catch {
      // 拉取失败保留上次状态
      return
    }
    if (status.value.status === 'running' && !pollActive.value) resumePolling()
  }

  /** 启动任务：成功后立即刷新状态并开启轮询 */
  async function start(configName: string): Promise<void> {
    if (busy.value || isRunning.value) return
    busy.value = true
    try {
      await runTask({ configName })
      await refresh()
    } finally {
      busy.value = false
    }
  }

  /** 停止任务：后端异步收尾时轮询保持开启，直至状态离开 running */
  async function stop(): Promise<void> {
    if (busy.value || !isRunning.value) return
    busy.value = true
    try {
      await stopTask()
      await refresh()
    } finally {
      busy.value = false
    }
  }

  return { status, busy, isRunning, refresh, start, stop }
}
