export type PowerTaskItem = {
  name: string
  id: string
  level: number
  levelName: string
  count: number
  runtimes: number
  autoDetect: boolean
}

export type TpLevel = {
  index: number
  name: string
}

export type TpTaskDefinition = {
  index: number
  id: string
  name: string
  cost: number
  maxSingleTimes: number
  levels: TpLevel[]
}

export type NewPowerTask = {
  taskIndex: number
  levelIndex: number
  count: number
  runtimes: number
  autoDetect: boolean
}

export type TaskConfig = {
  name: string
  startGame: {
    enabled: boolean
    'game.channel': number
    'game.path': string
    'game.useGlobalPath': boolean
    autologin: boolean
    relogin: boolean
    username?: string
    password?: string
  }
  trailblazePower: {
    enabled: boolean
    'replenish.enabled': boolean
    'replenish.times': number
    'replenish.way': number
    useAssistant: boolean
    useBuildTarget: boolean
    tasklist: PowerTaskItem[]
    'activity.enabled': boolean
    'activity.gardenOfPlenty.level1': number
    'activity.gardenOfPlenty.level2': number
    'activity.planarFissure.level': number
    'activity.realmOfTheStrange.level': number
  }
  receiveRewards: {
    enabled: boolean
    redeemCodes: string
    rewards: boolean[]
  }
  cosmicStrife: {
    enabled: boolean
    'pointRewards.enabled': boolean
    'divergentUniverse.enabled': boolean
    'divergentUniverse.mode': number
    'divergentUniverse.runtimes': number
    'divergentUniverse.useTechnique': boolean
    'currencyWars.enabled': boolean
    'currencyWars.mode': number
    'currencyWars.difficulty': number
    'currencyWars.reroll.bossAffixes': string
    'currencyWars.reroll.bossNames': string
    'currencyWars.reroll.investEnvironments': string
    'currencyWars.reroll.investStrategies': string
    'currencyWars.runtimes': number
    'currencyWars.strategy': string
    'currencyWars.strategyIndex': number
    'currencyWars.username': string
  }
  missionAccomplished: {
    enabled: boolean
    exitApp: boolean
    exitGame: boolean
    logout: boolean
    shutdown: boolean
    sleep: boolean
  }
  version: number
  [key: string]: unknown
}
