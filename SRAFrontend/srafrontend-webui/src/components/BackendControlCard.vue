<template>
  <PanelCard :title="t('W0032')">
    <div class="backend-control">
      <p class="hint">{{ t('W0033') }}</p>
      <div class="actions">
        <el-button type="warning" plain :icon="RefreshRight" class="control-btn" :loading="busy === 'restart'"
          :disabled="busy === 'stop'" @click="onRestart">
          {{ t('W0022') }}
        </el-button>
        <el-button type="danger" plain :icon="SwitchButton" class="control-btn" :loading="busy === 'stop'"
          :disabled="busy === 'restart'" @click="onStop">
          {{ t('W0028') }}
        </el-button>
      </div>
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { t } from '@/i18n'

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
    await ElMessageBox.confirm(t('W0021'), t('W0022'), {
      confirmButtonText: t('W0023'),
      cancelButtonText: t('W0024'),
      type: 'warning',
    })
  } catch {
    return
  }
  busy.value = 'restart'
  try {
    const message = await restartBackend()
    ElMessage.success(message || t('W0025'))
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : t('W0026'))
  } finally {
    busy.value = ''
  }
}

/** 停止后端：危险操作，二次确认后调用 /api/Backend/stop */
async function onStop() {
  try {
    await ElMessageBox.confirm(t('W0027'), t('W0028'), {
      confirmButtonText: t('W0029'),
      cancelButtonText: t('W0024'),
      type: 'warning',
    })
  } catch {
    return
  }
  busy.value = 'stop'
  try {
    const message = await stopBackend()
    ElMessage.success(message || t('W0030'))
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : t('W0031'))
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
