<template>
  <section :class="mobile ? 'mobile-stack' : 'page-wrap'">
  <section :class="mobile ? 'mobile-card' : 'panel page-panel'">
      <div class="section-head">
        <div>
          <p class="eyebrow">Settings</p>
          <h2>全局设置</h2>
        </div>
        <div class="editor-actions">
          <el-button :icon="Refresh" @click="$emit('load')">读取</el-button>
          <el-button :icon="Check" type="primary" @click="$emit('save')">保存设置</el-button>
        </div>
      </div>

      <el-tabs v-if="settingsModel" v-model="localSettingsTab" class="task-tabs">
        <el-tab-pane name="general" label="启动与识图">
          <div class="form-grid">
            <SwitchField label="自动检测游戏路径" active="开启" inactive="关闭" v-model="settingsModel.general['gamePath.autoDetect']" />
            <SwitchField label="启用启动参数" active="开启" inactive="关闭" v-model="settingsModel.general['gameArgs.enabled']" />
            <label class="field wide">
              <span>游戏路径列表（一行一个）</span>
              <el-input :model-value="gamePathsText" type="textarea" :rows="4" resize="none" @update:model-value="updateGamePaths" />
            </label>
            <label class="field">
              <span>当前路径索引</span>
              <el-input-number v-model="settingsModel.general['gamePath.index']" :min="0" :max="99" controls-position="right" />
            </label>
            <label class="field">
              <span>显示模式</span>
              <el-select v-model="settingsModel.general['gameArgs.fullScreenMode']">
                <el-option label="窗口化" value="窗口化" />
                <el-option label="全屏" value="全屏" />
              </el-select>
            </label>
            <label class="field">
              <span>窗口大小</span>
              <el-input v-model="settingsModel.general['gameArgs.windowSize']" placeholder="1920x1080" />
            </label>
            <SwitchField label="无边框窗口" active="开启" inactive="关闭" v-model="settingsModel.general['gameArgs.popupWindow']" />
            <SwitchField label="使用命令行启动" active="开启" inactive="关闭" v-model="settingsModel.general['gameArgs.useCmd']" />
            <label class="field">
              <span>OCR 置信度</span>
              <el-slider v-model="settingsModel.general.ocrMatchConfidence" :min="0" :max="1" :step="0.01" />
            </label>
            <label class="field">
              <span>模板匹配置信度</span>
              <el-slider v-model="settingsModel.general.templateMatchConfidence" :min="0" :max="1" :step="0.01" />
            </label>
            <label class="field">
              <span>停止热键</span>
              <el-input v-model="settingsModel.general['keybindings.stop']" />
            </label>
          </div>
        </el-tab-pane>

        <el-tab-pane name="remote" label="远程连接">
          <div class="form-grid">
            <label class="field wide">
              <span>WebUI 访问令牌</span>
              <el-input v-model="settingsModel.advanced['webui.remote.token']" type="password" show-password placeholder="starrailassistant" />
            </label>
            <SwitchField label="WebUI 服务状态记录" active="开启" inactive="关闭" v-model="settingsModel.advanced['webui.remote.enabled']" />
            <SwitchField label="WebUI 自启动记录" active="开启" inactive="关闭" v-model="settingsModel.advanced['webui.remote.autostart']" />
            <SwitchField label="外部 SRA 后端" active="使用" inactive="本机" v-model="settingsModel.advanced['backend.remote.enabled']" />
            <label class="field wide">
              <span>外部 SRA 后端地址</span>
              <el-input v-model="settingsModel.advanced['backend.remote.baseUrl']" placeholder="http://localhost:5000" />
            </label>
            <label class="field wide">
              <span>后端启动参数</span>
              <el-input v-model="settingsModel.advanced['backend.launchArgs']" placeholder="--inline" />
            </label>
          </div>
        </el-tab-pane>

        <el-tab-pane name="notification" label="通知">
          <div class="form-grid">
            <SwitchField label="启用通知" active="开启" inactive="关闭" v-model="settingsModel.notification.enabled" />
            <SwitchField label="系统通知" active="开启" inactive="关闭" v-model="settingsModel.notification['system.enabled']" />
          </div>
          <el-collapse class="settings-collapse">
            <el-collapse-item title="Webhook" name="webhook">
              <div class="form-grid compact">
                <SwitchField label="Webhook" active="开启" inactive="关闭" v-model="settingsModel.notification['webhook.enabled']" />
                <label class="field wide">
                  <span>Webhook URL</span>
                  <el-input v-model="settingsModel.notification['webhook.url']" />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="Bark" name="bark">
              <div class="form-grid compact">
                <SwitchField label="Bark" active="开启" inactive="关闭" v-model="settingsModel.notification['bark.enabled']" />
                <label class="field">
                  <span>Server URL</span>
                  <el-input v-model="settingsModel.notification['bark.serverUrl']" />
                </label>
                <label class="field">
                  <span>Device Key</span>
                  <el-input v-model="settingsModel.notification['bark.deviceKey']" type="password" show-password />
                </label>
                <label class="field">
                  <span>分组</span>
                  <el-input v-model="settingsModel.notification['bark.group']" />
                </label>
                <label class="field">
                  <span>铃声</span>
                  <el-input v-model="settingsModel.notification['bark.sound']" />
                </label>
                <label class="field">
                  <span>等级</span>
                  <el-input v-model="settingsModel.notification['bark.level']" />
                </label>
                <label class="field">
                  <span>图标 URL</span>
                  <el-input v-model="settingsModel.notification['bark.icon']" />
                </label>
                <label class="field">
                  <span>密文</span>
                  <el-input v-model="settingsModel.notification['bark.ciphertext']" type="password" show-password />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="钉钉" name="dingTalk">
              <div class="form-grid compact">
                <SwitchField label="钉钉" active="开启" inactive="关闭" v-model="settingsModel.notification['dingTalk.enabled']" />
                <label class="field wide">
                  <span>Webhook URL</span>
                  <el-input v-model="settingsModel.notification['dingTalk.webhookUrl']" />
                </label>
                <label class="field wide">
                  <span>Secret</span>
                  <el-input v-model="settingsModel.notification['dingTalk.secret']" type="password" show-password />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="Discord" name="discord">
              <div class="form-grid compact">
                <SwitchField label="Discord" active="开启" inactive="关闭" v-model="settingsModel.notification['discord.enabled']" />
                <SwitchField label="发送图片" active="开启" inactive="关闭" v-model="settingsModel.notification['discord.sendImage']" />
                <label class="field wide">
                  <span>Webhook URL</span>
                  <el-input v-model="settingsModel.notification['discord.webhookUrl']" />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="飞书" name="feishu">
              <div class="form-grid compact">
                <SwitchField label="飞书" active="开启" inactive="关闭" v-model="settingsModel.notification['feishu.enabled']" />
                <label class="field wide">
                  <span>Webhook URL</span>
                  <el-input v-model="settingsModel.notification['feishu.webhookUrl']" />
                </label>
                <label class="field">
                  <span>App ID</span>
                  <el-input v-model="settingsModel.notification['feishu.appId']" />
                </label>
                <label class="field">
                  <span>App Secret</span>
                  <el-input v-model="settingsModel.notification['feishu.appSecret']" type="password" show-password />
                </label>
                <label class="field">
                  <span>Receive ID</span>
                  <el-input v-model="settingsModel.notification['feishu.receiveId']" />
                </label>
                <label class="field">
                  <span>Receive ID Type</span>
                  <el-input v-model="settingsModel.notification['feishu.receiveIdType']" />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="OneBot" name="oneBot">
              <div class="form-grid compact">
                <SwitchField label="OneBot" active="开启" inactive="关闭" v-model="settingsModel.notification['oneBot.enabled']" />
                <SwitchField label="发送图片" active="开启" inactive="关闭" v-model="settingsModel.notification['oneBot.sendImage']" />
                <label class="field">
                  <span>服务地址</span>
                  <el-input v-model="settingsModel.notification['oneBot.url']" />
                </label>
                <label class="field">
                  <span>Token</span>
                  <el-input v-model="settingsModel.notification['oneBot.token']" type="password" show-password />
                </label>
                <label class="field">
                  <span>用户 ID</span>
                  <el-input v-model="settingsModel.notification['oneBot.userId']" />
                </label>
                <label class="field">
                  <span>群 ID</span>
                  <el-input v-model="settingsModel.notification['oneBot.groupId']" />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="Server 酱" name="serverChan">
              <div class="form-grid compact">
                <SwitchField label="Server 酱" active="开启" inactive="关闭" v-model="settingsModel.notification['serverChan.enabled']" />
                <label class="field wide">
                  <span>SendKey</span>
                  <el-input v-model="settingsModel.notification['serverChan.sendKey']" type="password" show-password />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="Telegram" name="telegram">
              <div class="form-grid compact">
                <SwitchField label="Telegram" active="开启" inactive="关闭" v-model="settingsModel.notification['telegram.enabled']" />
                <SwitchField label="发送图片" active="开启" inactive="关闭" v-model="settingsModel.notification['telegram.sendImage']" />
                <SwitchField label="使用代理" active="开启" inactive="关闭" v-model="settingsModel.notification['telegram.proxyEnabled']" />
                <label class="field">
                  <span>API Base URL</span>
                  <el-input v-model="settingsModel.notification['telegram.apiBaseUrl']" />
                </label>
                <label class="field">
                  <span>Bot Token</span>
                  <el-input v-model="settingsModel.notification['telegram.botToken']" type="password" show-password />
                </label>
                <label class="field">
                  <span>Chat ID</span>
                  <el-input v-model="settingsModel.notification['telegram.chatId']" />
                </label>
                <label class="field wide">
                  <span>代理地址</span>
                  <el-input v-model="settingsModel.notification['telegram.proxyUrl']" />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="企业微信" name="weCom">
              <div class="form-grid compact">
                <SwitchField label="企业微信" active="开启" inactive="关闭" v-model="settingsModel.notification['weCom.enabled']" />
                <SwitchField label="发送图片" active="开启" inactive="关闭" v-model="settingsModel.notification['weCom.sendImage']" />
                <label class="field wide">
                  <span>Webhook URL</span>
                  <el-input v-model="settingsModel.notification['weCom.webhookUrl']" />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="息息推" name="xxtui">
              <div class="form-grid compact">
                <SwitchField label="息息推" active="开启" inactive="关闭" v-model="settingsModel.notification['xxtui.enabled']" />
                <label class="field">
                  <span>API Key</span>
                  <el-input v-model="settingsModel.notification['xxtui.apiKey']" type="password" show-password />
                </label>
                <label class="field">
                  <span>频道</span>
                  <el-input v-model="settingsModel.notification['xxtui.channel']" />
                </label>
                <label class="field">
                  <span>来源</span>
                  <el-input v-model="settingsModel.notification['xxtui.source']" />
                </label>
              </div>
            </el-collapse-item>

            <el-collapse-item title="邮件" name="email">
              <div class="form-grid compact">
                <SwitchField label="邮件通知" active="开启" inactive="关闭" v-model="settingsModel.notification['email.enabled']" />
                <label class="field">
                  <span>SMTP 服务器</span>
                  <el-input v-model="settingsModel.notification['email.smtpServer']" />
                </label>
                <label class="field">
                  <span>SMTP 端口</span>
                  <el-input-number v-model="settingsModel.notification['email.smtpPort']" :min="1" :max="65535" controls-position="right" />
                </label>
                <label class="field">
                  <span>发件人</span>
                  <el-input v-model="settingsModel.notification['email.smtpSender']" />
                </label>
                <label class="field">
                  <span>收件人</span>
                  <el-input v-model="settingsModel.notification['email.smtpReceiver']" />
                </label>
                <label class="field wide">
                  <span>SMTP 授权码</span>
                  <el-input v-model="localEmailAuthCode" type="password" show-password placeholder="留空则不修改已有授权码" />
                </label>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-tab-pane>

        <el-tab-pane name="advanced-json" label="高级 JSON">
          <div class="json-toolbar">
            <span>用于排查或批量修改。常用设置建议使用上面的表单。</span>
            <div>
              <el-button @click="$emit('sync-json')">从表单同步</el-button>
              <el-button type="primary" @click="$emit('apply-json')">应用到表单</el-button>
            </div>
          </div>
          <el-input v-model="localSettingsText" class="settings-editor large" type="textarea" resize="none" spellcheck="false" />
        </el-tab-pane>
      </el-tabs>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Refresh } from '@element-plus/icons-vue'
import { SwitchField } from './formBits'
import type { SettingsModel } from '../types'

const props = withDefaults(defineProps<{
  settingsModel: SettingsModel | null
  settingsTab: string
  settingsText: string
  emailAuthCode: string
  mobile?: boolean
}>(), {
  mobile: false
})

const emit = defineEmits<{
  'update:settingsTab': [value: string]
  'update:settingsText': [value: string]
  'update:emailAuthCode': [value: string]
  'update-game-paths': [value: string | number]
  load: []
  save: []
  'sync-json': []
  'apply-json': []
}>()

const localSettingsTab = computed({
  get: () => props.settingsTab,
  set: (value: string) => emit('update:settingsTab', value)
})

const localSettingsText = computed({
  get: () => props.settingsText,
  set: (value: string) => emit('update:settingsText', value)
})

const localEmailAuthCode = computed({
  get: () => props.emailAuthCode,
  set: (value: string) => emit('update:emailAuthCode', value)
})

const gamePathsText = computed(() => (props.settingsModel?.general?.['gamePath.uris'] ?? []).join('\n'))

function updateGamePaths(value: string | number) {
  emit('update-game-paths', value)
}
</script>