import consoleAvatar from '@/assets/console-avatar.jpg'

export interface ThemeConfig {
  avatar: string
  backgrounds: {
    hero: string
    tasks: string
    settings: string
    extensions: string
    logs: string
  }
}

const theme: ThemeConfig = {
  avatar: consoleAvatar,
  backgrounds: {
    hero: "https://shasnow-1357811817.cos.ap-guangzhou.myqcloud.com/webui/00001.png",
    tasks: "",
    settings: "",
    extensions: "",
    logs: ""
  }
}

export default theme
