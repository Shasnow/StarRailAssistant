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
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { Check, Refresh } from '@element-plus/icons-vue'
import { SwitchField } from '@/components/formBits'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
</script>
