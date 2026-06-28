import type { SettingsModel } from '@/types'

export function createSettingsModel(source: unknown): SettingsModel {
  const raw = source && typeof source === 'object' ? (source as Partial<SettingsModel>) : {}
  return {
    ...raw,
    general: {
      'gamePath.index': 0,
      'gamePath.uris': [],
      'gamePath.autoDetect': true,
      'gameArgs.enabled': false,
      'gameArgs.fullScreenMode': '窗口化',
      'gameArgs.windowSize': '1920x1080',
      'gameArgs.popupWindow': false,
      'gameArgs.useCmd': false,
      'keybindings.stop': 'F9',
      ocrMatchConfidence: 0.7,
      templateMatchConfidence: 0.9,
      ...(raw.general ?? {})
    },
    advanced: {
      'backend.launchArgs': '--inline',
      'backend.remote.enabled': false,
      'backend.remote.baseUrl': 'http://localhost:5000',
      'webui.remote.enabled': false,
      'webui.remote.autostart': false,
      'webui.remote.token': 'starrailassistant',
      ...(raw.advanced ?? {})
    },
    notification: {
      enabled: false,
      'system.enabled': false,
      'webhook.enabled': false,
      'webhook.url': '',
      'bark.enabled': false,
      'bark.ciphertext': '',
      'bark.serverUrl': 'https://api.day.app',
      'bark.deviceKey': '',
      'bark.group': 'StarRailAssistant',
      'bark.icon': '',
      'bark.level': '',
      'bark.sound': '',
      'dingTalk.enabled': false,
      'dingTalk.secret': '',
      'dingTalk.webhookUrl': '',
      'discord.enabled': false,
      'discord.sendImage': false,
      'discord.webhookUrl': '',
      'feishu.enabled': false,
      'feishu.appId': '',
      'feishu.appSecret': '',
      'feishu.receiveId': '',
      'feishu.receiveIdType': '',
      'feishu.webhookUrl': '',
      'oneBot.enabled': false,
      'oneBot.sendImage': false,
      'oneBot.groupId': '',
      'oneBot.token': '',
      'oneBot.url': '',
      'oneBot.userId': '',
      'serverChan.enabled': false,
      'serverChan.sendKey': '',
      'telegram.enabled': false,
      'telegram.proxyEnabled': false,
      'telegram.sendImage': false,
      'telegram.apiBaseUrl': 'https://api.telegram.org',
      'telegram.botToken': '',
      'telegram.chatId': '',
      'telegram.proxyUrl': 'http://127.0.0.1:7890',
      'weCom.enabled': false,
      'weCom.sendImage': false,
      'weCom.webhookUrl': '',
      'xxtui.enabled': false,
      'xxtui.apiKey': '',
      'xxtui.channel': '',
      'xxtui.source': '',
      'email.enabled': false,
      'email.smtpServer': '',
      'email.smtpPort': 465,
      'email.smtpSender': '',
      'email.smtpReceiver': '',
      ...(raw.notification ?? {})
    },
    warpForecast: {
      'version.startDate': '',
      'version.days': 42,
      'monthlyCard.enabled': false,
      'version.compensationJade': 600,
      'scan.bag': true,
      'scan.eventGuide': true,
      'manual.currentJade': 0,
      'manual.specialPass': 0,
      'manual.normalPass': 0,
      'endgame.refreshCountOverride': -1,
      'weekly.countOverride': -1,
      ...(raw.warpForecast ?? {})
    }
  }
}

export function prepareSettingsForSave(model: SettingsModel, emailAuthCode: string): SettingsModel {
  const body = structuredClone(model)
  if (emailAuthCode) {
    body.notification ??= {}
    body.notification['email.smtpAuthCode'] = emailAuthCode
  }
  return body
}

