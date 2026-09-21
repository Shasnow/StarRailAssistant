import { useLocalStorage } from '@vueuse/core'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as configsApi from '@/api/configs'
import type { TasksConfigPayload } from '@/api/configs'
import { isCanceledError } from '@/api/http'

/**
 * 配置数据 store：连接 /api/Configs 服务与界面。
 *
 * state 分组：
 * - 配置名列表：names / namesLoading / namesError
 * - 当前配置：currentName（localStorage 持久化）/ currentConfig / detailLoading / detailError
 * - 写操作：saving / saveError
 */
export const useConfigsStore = defineStore('configs', () => {
  /* ---------- state ---------- */

  // 配置名列表
  const names = ref<string[]>([])
  const namesLoading = ref(false)
  const namesError = ref('')

  // 当前选中的配置名（跨会话持久化，写回由 VueUse 负责）
  const currentName = ref(useLocalStorage('sra_last_config', ''))
  const currentConfig = ref<TasksConfigPayload | null>(null)
  const detailLoading = ref(false)
  const detailError = ref('')

  // 保存/新建/删除等写操作的进行态
  const saving = ref(false)
  const saveError = ref('')

  /* ---------- getters ---------- */

  const configCount = computed(() => names.value.length)
  const hasCurrent = computed(() => currentName.value !== '' && currentConfig.value !== null)
  const isNamesLoaded = computed(() => namesError.value === '' && !namesLoading.value)

  /* ---------- actions ---------- */

  /** 拉取所有配置名列表 */
  async function fetchNames(signal?: AbortSignal): Promise<void> {
    namesLoading.value = true
    namesError.value = ''
    try {
      names.value = await configsApi.listConfigs(signal)
    } catch (err) {
      if (!isCanceledError(err)) {
        namesError.value = err instanceof Error ? err.message : String(err)
      }
    } finally {
      namesLoading.value = false
    }
  }

  /**
   * 读取指定配置到 currentConfig，并记录 currentName。
   * 返回配置负载（不存在时为 null），失败抛出原始错误由调用方决定展示方式
   * （错误信息已同步写入 detailError）。
   */
  async function loadConfig(name: string, signal?: AbortSignal): Promise<TasksConfigPayload | null> {
    currentName.value = name
    detailLoading.value = true
    detailError.value = ''
    try {
      currentConfig.value = await configsApi.getConfig(name, signal)
      return currentConfig.value
    } catch (err) {
      if (isCanceledError(err)) return null
      detailError.value = err instanceof Error ? err.message : String(err)
      throw err
    } finally {
      detailLoading.value = false
    }
  }

  /** 仅切换选中名（不发起请求）；持久化由 useLocalStorage 完成 */
  function selectName(name: string): void {
    currentName.value = name
  }

  /** 保存（更新）指定配置的内容 */
  async function saveConfig(name: string, data: TasksConfigPayload): Promise<boolean> {
    saving.value = true
    saveError.value = ''
    try {
      await configsApi.updateConfig(name, data)
      // 保存成功后同步本地缓存，避免未重新拉取时数据陈旧
      if (currentName.value === name) currentConfig.value = data
      return true
    } catch (err) {
      saveError.value = err instanceof Error ? err.message : String(err)
      return false
    } finally {
      saving.value = false
    }
  }

  /** 新建配置并刷新列表 */
  async function createConfig(name: string): Promise<boolean> {
    saving.value = true
    saveError.value = ''
    try {
      await configsApi.createConfig(name)
      await fetchNames()
      return true
    } catch (err) {
      saveError.value = err instanceof Error ? err.message : String(err)
      return false
    } finally {
      saving.value = false
    }
  }

  /** 删除配置并刷新列表；删除的是当前配置时清空选中态 */
  async function removeConfig(name: string): Promise<boolean> {
    saving.value = true
    saveError.value = ''
    try {
      await configsApi.removeConfig(name)
      if (currentName.value === name) {
        currentName.value = ''
        currentConfig.value = null
      }
      await fetchNames()
      return true
    } catch (err) {
      saveError.value = err instanceof Error ? err.message : String(err)
      return false
    } finally {
      saving.value = false
    }
  }

  /** 确保选中名有效：不在列表中时回退到第一个配置（列表为空则清空） */
  function normalizeSelection(): void {
    if (names.value.includes(currentName.value)) return
    currentName.value = names.value[0] ?? ''
  }

  return {
    // state
    names,
    namesLoading,
    namesError,
    currentName,
    currentConfig,
    detailLoading,
    detailError,
    saving,
    saveError,
    // getters
    configCount,
    hasCurrent,
    isNamesLoaded,
    // actions
    fetchNames,
    loadConfig,
    selectName,
    saveConfig,
    createConfig,
    removeConfig,
    normalizeSelection,
  }
})
