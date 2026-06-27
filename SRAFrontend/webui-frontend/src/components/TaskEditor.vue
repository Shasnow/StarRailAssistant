<template>
  <section :class="mobile ? 'mobile-card mobile-editor-card' : 'panel editor-panel'">
    <div class="section-head">
      <div>
        <p class="eyebrow">Mission Setup</p>
        <h2>{{ selectedConfig || '未选择配置' }}</h2>
      </div>
      <div class="editor-actions">
        <el-button :icon="Refresh" @click="$emit('load-detail')">重载</el-button>
        <el-button :icon="Check" type="primary" @click="$emit('save')">保存配置</el-button>
      </div>
    </div>

    <el-tabs v-model="localTaskTab" :class="['task-tabs', { 'mobile-tabs': mobile }]">
      <el-tab-pane name="start" label="启动游戏">
        <section v-if="configModel" class="form-section">
          <TaskHeader title="启动游戏" desc="配置渠道、路径与登录行为。" v-model="configModel.startGame.enabled" />
          <div class="form-grid">
            <label class="field">
              <span>渠道</span>
              <el-select v-model="configModel.startGame['game.channel']">
                <el-option label="官服" :value="0" />
                <el-option label="B 服" :value="1" />
                <el-option label="国际服" :value="2" />
              </el-select>
            </label>
            <label class="field wide">
              <span>游戏路径</span>
              <el-input v-model="configModel.startGame['game.path']" :disabled="configModel.startGame['game.useGlobalPath']" placeholder="使用全局路径时会忽略此项" />
            </label>
            <SwitchField label="路径来源" active="使用全局路径" inactive="单独配置" v-model="configModel.startGame['game.useGlobalPath']" />
            <SwitchField label="自动登录" active="开启" inactive="关闭" v-model="configModel.startGame.autologin" />
            <SwitchField label="重新登录" active="总是重新登录" inactive="保持现状" v-model="configModel.startGame.relogin" />
            <label class="field">
              <span>账号</span>
              <el-input v-model="localStartUsername" placeholder="留空则保留已保存账号" />
            </label>
            <label class="field">
              <span>密码</span>
              <el-input v-model="localStartPassword" type="password" show-password placeholder="留空则保留已保存密码" />
            </label>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane name="power" label="清体力">
        <section v-if="configModel" class="form-section">
          <TaskHeader title="清体力" desc="任务清单来自 SRA 内部设置项，避免手填 ID 出错。" v-model="configModel.trailblazePower.enabled" />

          <div class="sub-panel add-task-panel">
            <div class="sub-title">
              <strong>添加任务</strong>
              <span>{{ taskDefinitions.length ? '选择副本与关卡后加入清单' : '正在等待副本定义' }}</span>
            </div>
            <div class="add-task-grid">
              <label class="field">
                <span>副本类型</span>
                <el-select v-model="newPowerTask.taskIndex" filterable @change="resetNewPowerLevel">
                  <el-option v-for="task in taskDefinitions" :key="task.id" :label="task.name" :value="task.index" />
                </el-select>
              </label>
              <label class="field">
                <span>关卡</span>
                <el-select v-model="newPowerTask.levelIndex" filterable>
                  <el-option v-for="level in levelsForTask(newPowerTask.taskIndex)" :key="level.index" :label="level.name" :value="level.index" :disabled="level.index === 0" />
                </el-select>
              </label>
              <label class="field narrow">
                <span>单次次数</span>
                <el-input-number v-model="newPowerTask.count" :min="1" :max="maxSingleTimes(newPowerTask.taskIndex)" controls-position="right" />
              </label>
              <label class="field narrow">
                <span>运行次数</span>
                <el-input-number v-model="newPowerTask.runtimes" :min="0" :max="99999" controls-position="right" />
              </label>
              <SwitchField label="自动检测" active="开启" inactive="关闭" v-model="newPowerTask.autoDetect" />
              <el-button class="add-task-button" :icon="Plus" type="primary" @click="addPowerTask">加入清单</el-button>
            </div>
          </div>

          <div class="sub-panel">
            <div class="sub-title">
              <strong>任务清单</strong>
              <span>{{ taskListSummary }}</span>
            </div>
            <div v-if="!configModel.trailblazePower.tasklist.length" class="empty-hint">
              还没有任务。先在上方选择副本和关卡，再加入清单。
            </div>
            <div v-else class="power-list">
              <div v-for="(item, index) in configModel.trailblazePower.tasklist" :key="index" class="power-row">
                <div class="power-main">
                  <el-select :model-value="taskIndexForItem(item)" filterable @change="(value: string | number | boolean) => updatePowerTaskDefinition(item, Number(value))">
                    <el-option v-for="task in taskDefinitions" :key="task.id" :label="task.name" :value="task.index" />
                  </el-select>
                  <el-select v-model="item.level" filterable @change="updatePowerTaskLevel(item)">
                    <el-option v-for="level in levelsForItem(item)" :key="level.index" :label="level.name" :value="level.index" :disabled="level.index === 0" />
                  </el-select>
                </div>
                <div class="power-controls">
                  <label>
                    <span>单次</span>
                    <el-input-number v-model="item.count" :min="1" :max="maxSingleTimesForItem(item)" controls-position="right" />
                  </label>
                  <label>
                    <span>运行</span>
                    <el-input-number v-model="item.runtimes" :min="0" :max="99999" controls-position="right" />
                  </label>
                  <el-switch v-model="item.autoDetect" active-text="自动" inactive-text="固定" />
                  <el-button :icon="Delete" circle text type="danger" @click="removePowerTask(index)" />
                </div>
              </div>
            </div>
          </div>

          <div class="form-grid">
            <SwitchField label="补充体力" active="开启" inactive="关闭" v-model="configModel.trailblazePower['replenish.enabled']" />
            <label class="field">
              <span>补充方式</span>
              <el-select v-model="configModel.trailblazePower['replenish.way']">
                <el-option label="后备开拓力" :value="0" />
                <el-option label="燃料" :value="1" />
                <el-option label="星琼" :value="2" />
              </el-select>
            </label>
            <label class="field">
              <span>补充次数</span>
              <el-input-number v-model="configModel.trailblazePower['replenish.times']" :min="0" :max="99" controls-position="right" />
            </label>
            <SwitchField label="支援角色" active="使用" inactive="不使用" v-model="configModel.trailblazePower.useAssistant" />
            <SwitchField label="培养目标" active="优先完成" inactive="关闭" v-model="configModel.trailblazePower.useBuildTarget" />
            <SwitchField label="多倍活动检测" active="开启" inactive="关闭" v-model="configModel.trailblazePower['activity.enabled']" />
            <label class="field">
              <span>花萼繁生：金</span>
              <el-select v-model="configModel.trailblazePower['activity.gardenOfPlenty.level1']" filterable>
                <el-option v-for="level in levelsForTask(1)" :key="level.index" :label="level.name" :value="level.index" />
              </el-select>
            </label>
            <label class="field">
              <span>花萼繁生：赤</span>
              <el-select v-model="configModel.trailblazePower['activity.gardenOfPlenty.level2']" filterable>
                <el-option v-for="level in levelsForTask(2)" :key="level.index" :label="level.name" :value="level.index" />
              </el-select>
            </label>
            <label class="field">
              <span>侵蚀隧洞</span>
              <el-select v-model="configModel.trailblazePower['activity.realmOfTheStrange.level']" filterable>
                <el-option v-for="level in levelsForTask(4)" :key="level.index" :label="level.name" :value="level.index" />
              </el-select>
            </label>
            <label class="field">
              <span>饰品提取</span>
              <el-select v-model="configModel.trailblazePower['activity.planarFissure.level']" filterable>
                <el-option v-for="level in levelsForTask(0)" :key="level.index" :label="level.name" :value="level.index" />
              </el-select>
            </label>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane name="rewards" label="领取奖励">
        <section v-if="configModel" class="form-section">
          <TaskHeader title="领取奖励" desc="勾选要领取的奖励项目，兑换码支持空格或换行。" v-model="configModel.receiveRewards.enabled" />
          <div class="reward-grid">
            <el-checkbox v-for="(label, index) in rewardLabels" :key="label" v-model="configModel.receiveRewards.rewards[index]" border>
              {{ label }}
            </el-checkbox>
          </div>
          <label class="field block">
            <span>兑换码</span>
            <el-input v-model="configModel.receiveRewards.redeemCodes" type="textarea" :rows="5" resize="none" placeholder="兑换码 兑换码 兑换码" />
          </label>
        </section>
      </el-tab-pane>

      <el-tab-pane name="cosmic" label="旷宇纷争">
        <section v-if="configModel" class="form-section">
          <TaskHeader title="旷宇纷争" desc="管理差分宇宙、货币战争和积分奖励。" v-model="configModel.cosmicStrife.enabled" />
          <div class="sub-panel">
            <div class="sub-title">
              <strong>差分宇宙</strong>
              <el-switch v-model="configModel.cosmicStrife['divergentUniverse.enabled']" active-text="启用" inactive-text="关闭" />
            </div>
            <div class="form-grid compact">
              <label class="field">
                <span>模式</span>
                <el-select v-model="configModel.cosmicStrife['divergentUniverse.mode']">
                  <el-option label="刷第一关" :value="0" />
                </el-select>
              </label>
              <label class="field">
                <span>运行次数</span>
                <el-input-number v-model="configModel.cosmicStrife['divergentUniverse.runtimes']" :min="1" :max="99999" controls-position="right" />
              </label>
              <SwitchField label="秘技速刷" active="开启" inactive="关闭" v-model="configModel.cosmicStrife['divergentUniverse.useTechnique']" />
              <SwitchField label="积分奖励" active="开启" inactive="关闭" v-model="configModel.cosmicStrife['pointRewards.enabled']" />
            </div>
          </div>
          <div class="sub-panel">
            <div class="sub-title">
              <strong>货币战争</strong>
              <el-switch v-model="configModel.cosmicStrife['currencyWars.enabled']" active-text="启用" inactive-text="关闭" />
            </div>
            <div class="form-grid compact">
              <label class="field">
                <span>开拓者名称</span>
                <el-input v-model="configModel.cosmicStrife['currencyWars.username']" placeholder="角色名" />
              </label>
              <label class="field">
                <span>类型</span>
                <el-select v-model="configModel.cosmicStrife['currencyWars.mode']">
                  <el-option label="标准博弈" :value="0" />
                  <el-option label="超频博弈" :value="1" />
                  <el-option label="刷开局" :value="2" />
                </el-select>
              </label>
              <label class="field">
                <span>难度</span>
                <el-select v-model="configModel.cosmicStrife['currencyWars.difficulty']">
                  <el-option label="最低难度" :value="0" />
                  <el-option label="最高难度" :value="1" />
                  <el-option label="当前难度" :value="2" />
                </el-select>
              </label>
              <label class="field">
                <span>运行次数</span>
                <el-input-number v-model="configModel.cosmicStrife['currencyWars.runtimes']" :min="1" :max="99999" controls-position="right" />
              </label>
              <label class="field">
                <span>攻略名称</span>
                <el-input v-model="configModel.cosmicStrife['currencyWars.strategy']" placeholder="template" />
              </label>
              <label class="field">
                <span>攻略索引</span>
                <el-input-number v-model="configModel.cosmicStrife['currencyWars.strategyIndex']" :min="0" :max="9999" controls-position="right" />
              </label>
            </div>
            <el-collapse class="reroll-collapse">
              <el-collapse-item title="刷开局条件" name="reroll">
                <div class="form-grid compact">
                  <label class="field">
                    <span>Boss 名称</span>
                    <el-input v-model="configModel.cosmicStrife['currencyWars.reroll.bossNames']" />
                  </label>
                  <label class="field">
                    <span>Boss 词条</span>
                    <el-input v-model="configModel.cosmicStrife['currencyWars.reroll.bossAffixes']" />
                  </label>
                  <label class="field">
                    <span>投资环境</span>
                    <el-input v-model="configModel.cosmicStrife['currencyWars.reroll.investEnvironments']" />
                  </label>
                  <label class="field">
                    <span>投资策略</span>
                    <el-input v-model="configModel.cosmicStrife['currencyWars.reroll.investStrategies']" />
                  </label>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane name="finish" label="完成后">
        <section v-if="configModel" class="form-section">
          <TaskHeader title="任务完成后" desc="设置全部任务完成后的账号、游戏和电脑动作。" v-model="configModel.missionAccomplished.enabled" />
          <div class="finish-grid">
            <el-checkbox v-model="configModel.missionAccomplished.logout" border>登出当前账号</el-checkbox>
            <el-checkbox v-model="configModel.missionAccomplished.exitGame" border>退出游戏</el-checkbox>
            <el-checkbox v-model="configModel.missionAccomplished.exitApp" border>关闭程序</el-checkbox>
          </div>
          <div class="sub-panel">
            <div class="sub-title">
              <strong>电源动作</strong>
              <span>关机与休眠互斥</span>
            </div>
            <el-radio-group v-model="localPowerAction" class="power-actions">
              <el-radio-button label="none">无动作</el-radio-button>
              <el-radio-button label="shutdown">关机</el-radio-button>
              <el-radio-button label="sleep">休眠</el-radio-button>
            </el-radio-group>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane name="advanced" label="高级 JSON">
        <section class="form-section">
          <div class="json-toolbar">
            <span>用于排查和批量粘贴。日常修改建议使用表单。</span>
            <div>
              <el-button @click="$emit('sync-json')">从表单同步</el-button>
              <el-button type="primary" @click="$emit('apply-json')">应用到表单</el-button>
            </div>
          </div>
          <el-input v-model="localConfigText" class="json-editor" type="textarea" resize="none" spellcheck="false" />
        </section>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Delete, Plus, Refresh } from '@element-plus/icons-vue'
import { TaskHeader, SwitchField } from './formBits'
import type { NewPowerTask, PowerTaskItem, TaskConfig, TpTaskDefinition } from '../types'

const props = withDefaults(defineProps<{
  configModel: TaskConfig | null
  selectedConfig: string
  taskDefinitions: TpTaskDefinition[]
  newPowerTask: NewPowerTask
  rewardLabels: string[]
  taskTab: string
  configText: string
  startUsername: string
  startPassword: string
  mobile?: boolean
}>(), {
  mobile: false
})

const emit = defineEmits<{
  'update:taskTab': [value: string]
  'update:configText': [value: string]
  'update:startUsername': [value: string]
  'update:startPassword': [value: string]
  'load-detail': []
  save: []
  'sync-json': []
  'apply-json': []
}>()

const localTaskTab = computed({
  get: () => props.taskTab,
  set: (value: string) => emit('update:taskTab', value)
})

const localConfigText = computed({
  get: () => props.configText,
  set: (value: string) => emit('update:configText', value)
})

const localStartUsername = computed({
  get: () => props.startUsername,
  set: (value: string) => emit('update:startUsername', value)
})

const localStartPassword = computed({
  get: () => props.startPassword,
  set: (value: string) => emit('update:startPassword', value)
})

const taskListSummary = computed(() => {
  const count = props.configModel?.trailblazePower.tasklist.length ?? 0
  return count ? `${count} 个任务` : '暂无任务'
})

const localPowerAction = computed({
  get() {
    if (!props.configModel) return 'none'
    if (props.configModel.missionAccomplished.shutdown) return 'shutdown'
    if (props.configModel.missionAccomplished.sleep) return 'sleep'
    return 'none'
  },
  set(value: string) {
    if (!props.configModel) return
    props.configModel.missionAccomplished.shutdown = value === 'shutdown'
    props.configModel.missionAccomplished.sleep = value === 'sleep'
  }
})

function definitionByIndex(index: number) {
  return props.taskDefinitions.find((task) => task.index === index)
}

function definitionById(id: string) {
  return props.taskDefinitions.find((task) => task.id === id)
}

function levelsForTask(index: number) {
  return definitionByIndex(index)?.levels ?? []
}

function levelsForItem(item: PowerTaskItem) {
  return definitionById(item.id)?.levels ?? []
}

function maxSingleTimes(index: number) {
  return definitionByIndex(index)?.maxSingleTimes ?? 1
}

function maxSingleTimesForItem(item: PowerTaskItem) {
  return definitionById(item.id)?.maxSingleTimes ?? 1
}

function taskIndexForItem(item: PowerTaskItem) {
  return definitionById(item.id)?.index ?? 0
}

function resetNewPowerLevel() {
  props.newPowerTask.levelIndex = 0
  props.newPowerTask.count = Math.min(props.newPowerTask.count, maxSingleTimes(props.newPowerTask.taskIndex))
}

function addPowerTask() {
  if (!props.configModel) return
  const task = definitionByIndex(props.newPowerTask.taskIndex)
  const level = task?.levels.find((item) => item.index === props.newPowerTask.levelIndex)
  if (!task || !level || level.index === 0) return
  props.configModel.trailblazePower.tasklist.push({
    name: task.name,
    id: task.id,
    level: level.index,
    levelName: level.name,
    count: Math.min(props.newPowerTask.count, task.maxSingleTimes),
    runtimes: props.newPowerTask.runtimes,
    autoDetect: props.newPowerTask.autoDetect
  })
}

function updatePowerTaskDefinition(item: PowerTaskItem, taskIndex: number) {
  const task = definitionByIndex(taskIndex)
  if (!task) return
  item.id = task.id
  item.name = task.name
  item.level = 0
  item.levelName = ''
  item.count = Math.min(item.count, task.maxSingleTimes)
}

function updatePowerTaskLevel(item: PowerTaskItem) {
  const level = definitionById(item.id)?.levels.find((entry) => entry.index === item.level)
  item.levelName = level?.name ?? ''
}

function removePowerTask(index: number) {
  props.configModel?.trailblazePower.tasklist.splice(index, 1)
}
</script>