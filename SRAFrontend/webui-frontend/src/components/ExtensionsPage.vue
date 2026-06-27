<template>
  <section :class="mobile ? 'mobile-stack' : 'page-wrap'">
  <section :class="mobile ? 'mobile-card' : 'panel page-panel'">
      <div class="section-head">
        <div>
          <p class="eyebrow">Extensions</p>
          <h2>SRA 拓展</h2>
        </div>
        <div class="editor-actions">
          <el-button :icon="Refresh" @click="$emit('load-settings')">读取设置</el-button>
          <el-button :icon="Check" type="primary" @click="$emit('save-settings')">保存拓展设置</el-button>
        </div>
      </div>
      <div class="extension-grid">
        <section class="sub-panel">
          <div class="sub-title">
            <strong>自动对话</strong>
            <span>通过 SRA-cli trigger 控制</span>
          </div>
          <div class="form-grid compact">
            <SwitchField label="自动对话" active="启用" inactive="关闭" v-model="extensionState.autoPlotEnabled" />
            <SwitchField label="跳过剧情" active="跳过" inactive="保留" v-model="extensionState.skipPlot" />
          </div>
          <div class="panel-actions">
            <el-button :icon="Check" type="primary" @click="$emit('save-auto-plot')">应用自动对话</el-button>
          </div>
        </section>

        <section v-if="settingsModel" class="sub-panel">
          <div class="sub-title">
            <strong>抽卡资源预测</strong>
            <span>配置预测参数并可直接运行</span>
          </div>
          <div class="form-grid compact">
            <label class="field">
              <span>版本起始日期</span>
              <el-input v-model="settingsModel.warpForecast['version.startDate']" placeholder="YYYY-MM-DD" />
            </label>
            <label class="field">
              <span>版本天数</span>
              <el-input-number v-model="settingsModel.warpForecast['version.days']" :min="1" :max="999" controls-position="right" />
            </label>
            <SwitchField label="小月卡" active="持有" inactive="未持有" v-model="settingsModel.warpForecast['monthlyCard.enabled']" />
            <label class="field">
              <span>版本补偿星琼</span>
              <el-input-number v-model="settingsModel.warpForecast['version.compensationJade']" :min="0" :max="99999" controls-position="right" />
            </label>
            <SwitchField label="背包扫描" active="开启" inactive="关闭" v-model="settingsModel.warpForecast['scan.bag']" />
            <SwitchField label="奖励指南扫描" active="开启" inactive="关闭" v-model="settingsModel.warpForecast['scan.eventGuide']" />
            <label class="field">
              <span>当前星琼</span>
              <el-input-number v-model="settingsModel.warpForecast['manual.currentJade']" :min="0" :max="999999" controls-position="right" />
            </label>
            <label class="field">
              <span>星轨专票</span>
              <el-input-number v-model="settingsModel.warpForecast['manual.specialPass']" :min="0" :max="99999" controls-position="right" />
            </label>
            <label class="field">
              <span>星轨通票</span>
              <el-input-number v-model="settingsModel.warpForecast['manual.normalPass']" :min="0" :max="99999" controls-position="right" />
            </label>
            <label class="field">
              <span>深渊刷新次数覆写</span>
              <el-input-number v-model="settingsModel.warpForecast['endgame.refreshCountOverride']" :min="-1" :max="99" controls-position="right" />
            </label>
            <label class="field">
              <span>周常次数覆写</span>
              <el-input-number v-model="settingsModel.warpForecast['weekly.countOverride']" :min="-1" :max="99" controls-position="right" />
            </label>
          </div>
          <div class="panel-actions">
            <el-button :icon="Check" @click="$emit('save-settings')">保存预测设置</el-button>
            <el-button :icon="VideoPlay" type="primary" @click="$emit('run-warp-forecast')">运行预测</el-button>
          </div>
        </section>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { Check, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { SwitchField } from './formBits'
import type { SettingsModel } from '../types'

withDefaults(defineProps<{
  settingsModel: SettingsModel | null
  extensionState: {
    autoPlotEnabled: boolean
    skipPlot: boolean
  }
  mobile?: boolean
}>(), {
  mobile: false
})

defineEmits<{
  'load-settings': []
  'save-settings': []
  'save-auto-plot': []
  'run-warp-forecast': []
}>()
</script>
