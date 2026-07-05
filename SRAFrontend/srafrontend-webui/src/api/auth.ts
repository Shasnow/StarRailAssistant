import request from './request'

export function auth(token: string) {
  return request.post('/auth', { token })
}
