import type { TaskConfig } from '@/types'

type Credentials = {
  username?: string
  password?: string
}

export function createConfigModel(source: unknown, fallbackName: string): TaskConfig {
  const raw = source && typeof source === 'object' ? (source as Partial<TaskConfig>) : {}
  const model: TaskConfig = {
    ...raw,
    name: String(raw.name ?? fallbackName ?? 'Default'),
    startGame: {
      enabled: true,
      'game.channel': 0,
      'game.path': '',
      'game.useGlobalPath': true,
      autologin: true,
      relogin: true,
      ...(raw.startGame ?? {})
    },
    trailblazePower: {
      enabled: false,
      'replenish.enabled': false,
      'replenish.times': 0,
      'replenish.way': 0,
      useAssistant: false,
      useBuildTarget: false,
      tasklist: [],
      'activity.enabled': false,
      'activity.gardenOfPlenty.level1': 0,
      'activity.gardenOfPlenty.level2': 0,
      'activity.planarFissure.level': 0,
      'activity.realmOfTheStrange.level': 0,
      ...(raw.trailblazePower ?? {})
    },
    receiveRewards: {
      enabled: false,
      redeemCodes: '',
      rewards: [true, true, true, true, true, true, false],
      ...(raw.receiveRewards ?? {})
    },
    cosmicStrife: {
      enabled: false,
      'pointRewards.enabled': false,
      'divergentUniverse.enabled': false,
      'divergentUniverse.mode': 0,
      'divergentUniverse.runtimes': 1,
      'divergentUniverse.useTechnique': false,
      'currencyWars.enabled': false,
      'currencyWars.mode': 0,
      'currencyWars.difficulty': 0,
      'currencyWars.reroll.bossAffixes': '',
      'currencyWars.reroll.bossNames': '',
      'currencyWars.reroll.investEnvironments': '',
      'currencyWars.reroll.investStrategies': '',
      'currencyWars.runtimes': 1,
      'currencyWars.strategy': 'template',
      'currencyWars.strategyIndex': 0,
      'currencyWars.username': '',
      ...(raw.cosmicStrife ?? {})
    },
    missionAccomplished: {
      enabled: false,
      exitApp: false,
      exitGame: false,
      logout: false,
      shutdown: false,
      sleep: false,
      ...(raw.missionAccomplished ?? {})
    },
    version: Number(raw.version ?? 4)
  }
  delete model.startGame.username
  delete model.startGame.password
  normalizeConfig(model)
  return model
}

export function normalizeConfig(model: TaskConfig) {
  model.receiveRewards.rewards = Array.from({ length: 7 }, (_, index) => Boolean(model.receiveRewards.rewards?.[index]))
  model.trailblazePower.tasklist = Array.isArray(model.trailblazePower.tasklist)
    ? model.trailblazePower.tasklist.map((item) => ({
        name: item?.name ?? '',
        id: item?.id ?? '',
        level: Number(item?.level ?? 0),
        levelName: item?.levelName ?? '',
        count: Number(item?.count ?? 1),
        runtimes: Number(item?.runtimes ?? 0),
        autoDetect: Boolean(item?.autoDetect)
      }))
    : []
}

export function prepareConfigForSave(model: TaskConfig, credentials: Credentials): TaskConfig {
  const body = structuredClone(model)
  normalizeConfig(body)
  delete body.startGame.username
  delete body.startGame.password
  if (credentials.username?.trim()) body.startGame.username = credentials.username.trim()
  if (credentials.password) body.startGame.password = credentials.password
  return body
}

