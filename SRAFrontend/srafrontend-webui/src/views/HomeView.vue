<template>
  <div class="dashboard">
    <!-- 左栏：运行状态 + 配置选择 -->
    <aside class="col col-left">
      <StatusCard :status="taskStatus" />
      <ConfigCard :model-value="selectedConfig" :configs="configsStore.names" :running="taskRunning" :busy="taskBusy"
        :loading="configsStore.namesLoading" :error="configsStore.namesError" :saving="configsStore.saving"
        @retry="configsStore.fetchNames()" @update:model-value="handleConfigChange" @start="handleStart"
        @stop="handleStop" @create="handleConfigCreate" @remove="handleConfigRemove" />
    </aside>

    <!-- 中栏：OpenAPI 驱动的任务配置 -->
    <section class="col col-center">
      <TasksConfigPanel ref="configPanel" :exclude-keys="['name', 'version']" :config-name="selectedConfig" />
    </section>

    <!-- 右栏：公告 -->
    <aside class="col col-right">
      <AnnouncementCard />
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import AnnouncementCard from '@/components/AnnouncementCard.vue'
import ConfigCard from '@/components/ConfigCard.vue'
import StatusCard from '@/components/StatusCard.vue'
import TasksConfigPanel from '@/components/TasksConfigPanel.vue'
import { useTaskRunner } from '@/composables/useTaskRunner'
import { useConfigsStore } from '@/stores/configs'

// 配置列表来自后端 /api/Configs；选中名由 store 持久化到 localStorage
const configsStore = useConfigsStore()
const selectedConfig = computed({
  get: () => configsStore.currentName,
  set: (value) => configsStore.selectName(value),
})

// 任务运行控制：启动 / 停止 / 1s 状态轮询（驱动状态卡片）
const task = useTaskRunner()
// 顶层解包：模板中自动去 ref
const taskStatus = task.status
const taskBusy = task.busy
const taskRunning = task.isRunning

// 中栏配置面板：暴露 isDirty / save，切换配置前用于未保存更改检查
const configPanel = ref<InstanceType<typeof TasksConfigPanel>>()

/**
 * 切换配置：有未保存的更改时弹窗确认——
 * 「保存并切换」成功后切换（保存失败留在当前配置）；
 * 「放弃更改」直接切换；关闭弹窗则留在当前配置。
 */
async function handleConfigChange(next: string) {
  if (next === selectedConfig.value) return
  const panel = configPanel.value
  if (panel?.isDirty) {
    try {
      await ElMessageBox.confirm(
        `配置「${selectedConfig.value}」有未保存的更改，切换前是否保存？`,
        '未保存的更改',
        {
          confirmButtonText: '保存并切换',
          cancelButtonText: '放弃更改',
          distinguishCancelAndClose: true,
          type: 'warning',
        },
      )
      // 保存并切换：保存失败则留在当前配置
      if (!(await panel.save())) return
    } catch (action) {
      // cancel = 放弃更改并继续切换；close（ESC / 右上角关闭）= 留在当前配置
      if (action !== 'cancel') return
    }
  }
  selectedConfig.value = next
}

/** 新建配置：成功后切换到新配置（复用切换流程，保留未保存更改检查） */
async function handleConfigCreate(name: string) {
  if (!(await configsStore.createConfig(name))) {
    ElMessage.error(configsStore.saveError || '新建配置失败')
    return
  }
  ElMessage.success(`配置「${name}」已创建`)
  await handleConfigChange(name)
}

/** 删除配置：删除的是当前配置时回退选中第一个剩余配置 */
async function handleConfigRemove(name: string) {
  if (!(await configsStore.removeConfig(name))) {
    ElMessage.error(configsStore.saveError || '删除配置失败')
    return
  }
  ElMessage.success(`配置「${name}」已删除`)
  configsStore.normalizeSelection()
}

onMounted(async () => {
  await configsStore.fetchNames()
  configsStore.normalizeSelection()
  // 同步后端任务状态：已在运行则恢复轮询驱动状态卡片
  void task.refresh()
})

/** 启动任务：以当前选中配置运行，结果通过消息提示 */
async function handleStart() {
  if (!selectedConfig.value) {
    ElMessage.warning('请先选择运行配置')
    return
  }
  try {
    await task.start(selectedConfig.value)
    ElMessage.success('任务已启动')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '启动任务失败')
  }
}

/** 停止任务：后端异步收尾，状态卡片由轮询更新 */
async function handleStop() {
  try {
    await task.stop()
    ElMessage.success('已发送停止指令')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '停止任务失败')
  }
}
</script>

<style scoped>
/* 左-中-右三栏：两侧固定宽度区间，中间自适应；窄屏下折叠为单列 */
.dashboard {
  min-height: 80vh;
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 24px 48px;
  display: grid;
  grid-template-columns: minmax(260px, 300px) minmax(0, 1fr) minmax(260px, 300px);
  gap: 20px;
  align-items: start;
}

.col {
  display: grid;
  gap: 20px;
  align-content: start;
  min-width: 0;
}

@media (max-width: 1199px) {
  .dashboard {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .dashboard {
    padding: 20px 16px 32px;
  }
}
</style>
