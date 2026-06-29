import request from './request'

export function verifyToken(token: string) {
  return request.post('/Auth/verify', { token })
}
