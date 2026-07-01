export const GREETINGS_ZH = [
  '欢迎使用 SRA',
  '坐和放宽',
  "并非\n'Sequence Read Archive'",
  '启动器启动启动器',
  '-1073741819',
  '飞荧扑火，向死而生',
  '跨越寰宇终抵黯淡星外',
  '立志成为崩铁糕手',
  'Bon voyage',
  'May your path be clear',
  'May you get to where\ndreams are all\ncrystalline and sweet',
  '我们将在过去篆刻未来',
  '铁花飞，飘逸不残灰'
]

export function randomGreeting() {
  return GREETINGS_ZH[Math.floor(Math.random() * GREETINGS_ZH.length)]
}
