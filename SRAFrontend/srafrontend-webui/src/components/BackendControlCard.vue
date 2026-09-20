<template>
  <PanelCard title="后端控制">
    <div class="backend-control">
      <p class="hint">重启会中断运行中的任务；停止后日志与实时画面将断开，需手动重启后端才能恢复。</p>
      <div class="actions">
        <el-button type="warning" plain :icon="RefreshRight" class="control-btn" :loading="busy === 'restart'"
          :disabled="busy === 'stop'" @click="onRestart">
          重启后端
        </el-button>
        <el-button type="danger" plain :icon="SwitchButton" class="control-btn" :loading="busy === 'stop'"
          :disabled="busy === 'restart'" @click="onStop">
          停止后端
        </el-button>
      </div>
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, SwitchButton } from '@element-plus/icons-vue'
import { ref } from 'vue'
import PanelCard from './PanelCard.vue'
import { restartBackend, stopBackend } from '@/api/backend'

/** 当前进行中的操作，用于按钮 loading / 互斥禁用 */
const busy = ref<'' | 'restart' | 'stop'>('')

/** 重启后端：危险操作，二次确认后调用 /api/Backend/restart */
async function onRestart() {
  try {
    await ElMessageBox.confirm('确定重启后端服务？运行中的任务将被中断。', '重启后端', {
      confirmButtonText: '重启',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  busy.value = 'restart'
  try {
    const message = await restartBackend()
    ElMessage.success(message || '重启指令已发送')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '重启后端失败')
  } finally {
    busy.value = ''
  }
}

/** 停止后端：危险操作，二次确认后调用 /api/Backend/stop */
async function onStop() {
  try {
    await ElMessageBox.confirm('确定停止后端服务？停止后需手动重启才能恢复。', '停止后端', {
      confirmButtonText: '停止',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  busy.value = 'stop'
  try {
    const message = await stopBackend()
    ElMessage.success(message || '停止指令已发送')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '停止后端失败')
  } finally {
    busy.value = ''
  }
}
</script>

<style scoped>
.backend-control {
  display: grid;
  gap: 14px;
}

.hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text);
  opacity: 0.68;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

/* el-button 相邻自带 margin-left，栅格布局下用 gap 控制间距 */
.control-btn {
  width: 100%;
  margin: 0;
}
</style>
