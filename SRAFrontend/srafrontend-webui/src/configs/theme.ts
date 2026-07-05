import consoleAvatar from '@/assets/console-avatar.jpg'

export interface ThemeColors {
  primary: string
  primaryLight: string
  primaryDark: string
  accent: string
  success: string
  danger: string
  warning: string
  text: string
  textSecondary: string
  textMuted: string
  bgBody: string
  bgCard: string
  bgGlass: string
  border: string
  borderLight: string
  shadow: string
}

export interface ThemeSpacing {
  xs: string
  sm: string
  md: string
  lg: string
  xl: string
  '2xl': string
  '3xl': string
  '4xl': string
}

export interface ThemeRadius {
  sm: string
  md: string
  lg: string
  xl: string
  full: string
}

export interface ThemeShadows {
  sm: string
  md: string
  lg: string
  xl: string
}

export interface ThemeConfig {
  avatar: string
  backgrounds: {
    hero: string
    tasks: string
    settings: string
    extensions: string
    logs: string
  }
  colors: ThemeColors
  spacing: ThemeSpacing
  radius: ThemeRadius
  shadows: ThemeShadows
}

const theme: ThemeConfig = {
  avatar: consoleAvatar,
  backgrounds: {
    hero: "https://shasnow-1357811817.cos.ap-guangzhou.myqcloud.com/webui/00001.png",
    tasks: "",
    settings: "",
    extensions: "",
    logs: ""
  },
  colors: {
    primary: '#6f63e8',
    primaryLight: '#8378ff',
    primaryDark: '#5a4fd4',
    accent: '#c79cff',
    success: '#6bd59a',
    danger: '#ff8cad',
    warning: '#f4b8dc',
    text: '#293154',
    textSecondary: '#667085',
    textMuted: '#a0a8c0',
    bgBody: '#f7f8ff',
    bgCard: '#ffffff',
    bgGlass: 'rgba(255, 255, 255, 0.74)',
    border: 'rgba(118, 150, 255, 0.12)',
    borderLight: 'rgba(255, 255, 255, 0.46)',
    shadow: 'rgba(72, 82, 154, 0.13)'
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    '2xl': '48px',
    '3xl': '64px',
    '4xl': '96px'
  },
  radius: {
    sm: '6px',
    md: '10px',
    lg: '16px',
    xl: '24px',
    full: '9999px'
  },
  shadows: {
    sm: '0 2px 8px rgba(72, 82, 154, 0.08)',
    md: '0 8px 22px rgba(72, 82, 154, 0.12)',
    lg: '0 18px 48px rgba(72, 82, 154, 0.13)',
    xl: '0 24px 60px rgba(72, 82, 154, 0.16)'
  }
}

export function applyTheme(t: ThemeConfig = theme) {
  const root = document.documentElement
  const vars: Record<string, string> = {}

  for (const [key, value] of Object.entries(t.colors)) vars[`--color-${kebab(key)}`] = value
  for (const [key, value] of Object.entries(t.spacing)) vars[`--spacing-${key}`] = value
  for (const [key, value] of Object.entries(t.radius)) vars[`--radius-${kebab(key)}`] = value
  for (const [key, value] of Object.entries(t.shadows)) vars[`--shadow-${key}`] = value

  for (const [name, value] of Object.entries(vars)) root.style.setProperty(name, value)
}

function kebab(s: string): string {
  return s.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
}

export default theme
