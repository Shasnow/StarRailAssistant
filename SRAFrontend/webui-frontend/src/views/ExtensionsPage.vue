<template>
  <section class="page-wrap">
    <section class="panel page-panel">
      <div class="page-banner">
        <div class="page-banner-copy">
          <p class="eyebrow">Extensions</p>
          <h2>SRA 拓展</h2>
          <p>围绕常用拓展做成可直达的控制区，减少跳转，也让后端状态更容易被看见。</p>
        </div>
        <div class="page-banner-actions">
          <el-button :icon="Refresh" @click="app.loadSettings()">读取设置</el-button>
          <el-button :icon="Check" type="primary" @click="app.saveSettingsGui()">保存拓展设置</el-button>
        </div>
      </div>
      <div class="extension-grid">
        <section class="sub-panel extension-card auto-plot-card">
          <div class="sub-title">
            <strong>自动对话</strong>
            <span>通过 SRA-cli trigger 控制</span>
          </div>
          <div class="extension-mini-copy">
            适合临时开启剧情自动处理，改动会直接写入后端设置。
          </div>
          <div class="extension-toggle-list">
            <SwitchField label="自动对话" active="启用" inactive="关闭" v-model="app.extensionState.autoPlotEnabled" />
            <SwitchField label="跳过剧情" active="跳过" inactive="保留" v-model="app.extensionState.skipPlot" />
          </div>
          <div class="panel-actions compact-actions">
            <el-button :icon="Check" type="primary" @click="app.saveAutoPlot()">应用自动对话</el-button>
          </div>
        </section>

        <section v-if="app.settingsModel" class="sub-panel extension-card warp-forecast-card">
          <div class="sub-title">
            <strong>抽卡资源预测</strong>
            <span>配置预测参数并可直接运行</span>
          </div>
          <div class="extension-section-grid">
            <div class="extension-section">
              <p>版本</p>
              <div class="form-grid compact">
                <label class="field">
                  <span>版本起始日期</span>
                  <el-input v-model="app.settingsModel.warpForecast['version.startDate']" placeholder="YYYY-MM-DD" />
                </label>
                <label class="field">
                  <span>版本天数</span>
                  <el-input-number v-model="app.settingsModel.warpForecast['version.days']" :min="1" :max="999" controls-position="right" />
                </label>
                <label class="field">
                  <span>版本补偿星琼</span>
                  <el-input-number v-model="app.settingsModel.warpForecast['version.compensationJade']" :min="0" :max="99999" controls-position="right" />
                </label>
              </div>
            </div>

            <div class="extension-section">
              <p>扫描</p>
              <div class="extension-toggle-list two-column">
                <SwitchField label="小月卡" active="持有" inactive="未持有" v-model="app.settingsModel.warpForecast['monthlyCard.enabled']" />
                <SwitchField label="背包扫描" active="开启" inactive="关闭" v-model="app.settingsModel.warpForecast['scan.bag']" />
                <SwitchField label="奖励指南扫描" active="开启" inactive="关闭" v-model="app.settingsModel.warpForecast['scan.eventGuide']" />
              </div>
            </div>

            <div class="extension-section wide">
              <p>手动数量与覆写</p>
              <div class="form-grid compact">
                <label class="field">
                  <span>当前星琼</span>
                  <el-input-number v-model="app.settingsModel.warpForecast['manual.currentJade']" :min="0" :max="999999" controls-position="right" />
                </label>
                <label class="field">
                  <span>星轨专票</span>
                  <el-input-number v-model="app.settingsModel.warpForecast['manual.specialPass']" :min="0" :max="99999" controls-position="right" />
                </label>
                <label class="field">
                  <span>星轨通票</span>
                  <el-input-number v-model="app.settingsModel.warpForecast['manual.normalPass']" :min="0" :max="99999" controls-position="right" />
                </label>
                <label class="field">
                  <span>深渊刷新次数覆写</span>
                  <el-input-number v-model="app.settingsModel.warpForecast['endgame.refreshCountOverride']" :min="-1" :max="99" controls-position="right" />
                </label>
                <label class="field">
                  <span>周常次数覆写</span>
                  <el-input-number v-model="app.settingsModel.warpForecast['weekly.countOverride']" :min="-1" :max="99" controls-position="right" />
                </label>
              </div>
            </div>
          </div>
          <div class="panel-actions">
            <el-button :icon="Check" @click="app.saveSettingsGui()">保存预测设置</el-button>
            <el-button :icon="VideoPlay" type="primary" @click="app.runWarpForecast()">运行预测</el-button>
          </div>
        </section>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { Check, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { SwitchField } from '@/components/formBits'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
</script>
