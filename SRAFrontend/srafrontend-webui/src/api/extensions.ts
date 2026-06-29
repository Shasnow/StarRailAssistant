import request from './request'

export function saveAutoPlot(enabled: boolean, skipPlot: boolean) {
  return request.post('/Extensions/auto-plot', { enabled, skipPlot })
}

export function runWarpForecast() {
  return request.post('/Extensions/warp-forecast/run')
}
