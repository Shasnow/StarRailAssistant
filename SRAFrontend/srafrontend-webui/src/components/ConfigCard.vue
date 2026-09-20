<template>
  <PanelCard title="配置选择">
    <div class="config-form">
      <!-- 运行中锁定配置，避免运行时切换方案 -->
      <el-select :model-value="modelValue" class="config-select" placeholder="选择运行配置" :disabled="running"
        :loading="loading" @update:model-value="$emit('update:modelValue', $event)">
        <el-option v-for="c in configs" :key="c" :label="c" :value="c" />
      </el-select>

      <!-- 列表加载失败：错误提示 + 重试 -->
      <div v-if="error" class="config-error" role="alert">
        <span class="error-text">{{ error }}</span>
        <el-button size="small" text type="primary" @click="$emit('retry')">重试</el-button>
      </div>

      <!-- 配置管理：新建（弹窗输入名称）/ 删除（二次确认）当前选中配置 -->
      <div class="manage">
        <el-button type="primary" plain :icon="Plus" class="manage-btn" :disabled="running || saving" @click="onCreate">
          新建
        </el-button>
        <el-button type="danger" plain :icon="Delete" class="manage-btn" :disabled="running || saving || !modelValue"
          @click="onRemove">
          删除
        </el-button>
      </div>

      <div class="actions">
        <el-button type="success" :icon="VideoPlay" class="action-btn" :disabled="running || busy"
          @click="$emit('start')">
          启动
        </el-button>
        <el-button type="danger" :icon="VideoPause" class="action-btn" :disabled="!running || busy"
          @click="$emit('stop')">
          停止
        </el-button>
      </div>
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { ElMessageBox } from 'element-plus'
import { Delete, Plus, VideoPause, VideoPlay } from '@element-plus/icons-vue'
import PanelCard from './PanelCard.vue'

const props = withDefaults(
  defineProps<{
    configs: string[]
    modelValue: string
    running: boolean
    /** 配置名列表加载中 */
    loading?: boolean
    /** 配置名列表加载失败的错误信息 */
    error?: string
    /** 新建/删除等写操作进行中，禁用管理按钮防重复提交 */
    saving?: boolean
    /** 启动/停止任务请求进行中，禁用两个操作按钮防重复提交 */
    busy?: boolean
  }>(),
  { loading: false, error: '', saving: false, busy: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  start: []
  stop: []
  /** 重新拉取配置名列表 */
  retry: []
  /** 新建配置，name 来自弹窗输入（已非空校验） */
  create: [name: string]
  /** 删除当前选中的配置 */
  remove: [name: string]
}>()

/** 新建：弹窗收集配置名，确认后向上派发（名称合法性 / 重名由后端校验） */
async function onCreate() {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的配置名称', '新建配置', {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputPattern: /\S/,
      inputErrorMessage: '配置名不能为空',
    })
    const name = value.trim()
    if (name) emit('create', name)
  } catch {
    // 取消输入
  }
}

/** 删除当前选中配置：危险操作，二次确认后向上派发 */
async function onRemove() {
  try {
    await ElMessageBox.confirm(`确定删除配置「${props.modelValue}」？该操作不可恢复。`, '删除配置', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  emit('remove', props.modelValue)
}
</script>

<style scoped>
.config-form {
  display: grid;
  gap: 14px;
}

.config-select {
  width: 100%;
}

.config-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--color-danger);
}

.error-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

/* 新建/删除管理行：与 actions 同款栅格，el-button 相邻 margin 归零 */
.manage {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.manage-btn {
  width: 100%;
  margin: 0;
}

/* el-button 相邻自带 margin-left，栅格布局下用 gap 控制间距 */
.action-btn {
  width: 100%;
  margin: 0;
}
</style>
