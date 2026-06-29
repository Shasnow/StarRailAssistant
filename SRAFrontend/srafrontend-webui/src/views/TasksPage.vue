<template>
  <section class="desktop-layout">
    <aside class="desktop-rail">
      <RuntimeCard
        :status="app.sraStatus"
        :health-ok="app.health.ok"
        @refresh="app.refreshAll"
        @start="app.startTask"
        @stop="app.stopTask"
      />

      <ConfigCard
        v-model:selected-config="app.selectedConfig"
        v-model:draft="app.configNameDraft"
        :config-names="app.configNames"
        @load-configs="app.loadConfigs"
        @load-detail="app.loadConfigDetail"
        @create="app.createConfig"
        @save="app.saveConfig"
        @open-settings="$router.push('/settings')"
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

    <section class="desktop-stage">
      <TaskEditor
        v-model:task-tab="taskTab"
        v-model:config-text="app.configText"
        v-model:start-username="app.startUsername"
        v-model:start-password="app.startPassword"
        :config-model="app.configModel"
        :selected-config="app.selectedConfig"
        :task-definitions="app.taskDefinitions"
        :new-power-task="app.newPowerTask"
        :reward-labels="app.rewardLabels"
        @load-detail="app.loadConfigDetail"
        @save="app.saveConfig"
        @sync-json="app.syncJsonFromForm"
        @apply-json="app.applyJsonToForm"
      />
    </section>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '@/stores/app'
import RuntimeCard from '@/components/RuntimeCard.vue'
import ConfigCard from '@/components/ConfigCard.vue'
import TaskEditor from '@/components/TaskEditor.vue'

const app = useAppStore()
const taskTab = ref('start')
</script>
