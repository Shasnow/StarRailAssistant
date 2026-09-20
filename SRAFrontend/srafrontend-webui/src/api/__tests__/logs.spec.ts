import { describe, expect, it } from 'vitest'
import { LOG_LEVELS, LOG_STREAM_URL, parseLogPayload } from '../logs'

describe('logs api', () => {
  it('SSE 端点指向 /api/backend/logs/stream', () => {
    expect(LOG_STREAM_URL).toBe('/api/backend/logs/stream')
  })

  describe('parseLogPayload', () => {
    it('解析标准 JSON 负载（级别大小写归一化）', () => {
      const entry = parseLogPayload(
        JSON.stringify({ level: 'error', message: 'boom', timestamp: '10:00:00' }),
      )
      expect(entry).toEqual({ level: 'ERROR', message: 'boom', timestamp: '10:00:00' })
    })

    it('缺失字段回退默认值：级别 INFO、时间戳取当前时间', () => {
      const entry = parseLogPayload(JSON.stringify({ message: 'hello' }))
      expect(entry.level).toBe('INFO')
      expect(entry.message).toBe('hello')
      expect(entry.timestamp).toMatch(/^\d{2}:\d{2}:\d{2}$/)
    })

    it('未知级别回退 INFO', () => {
      const entry = parseLogPayload(JSON.stringify({ level: 'trace', message: 'x' }))
      expect(entry.level).toBe('INFO')
    })

    it('message 非字符串时回退为原始负载文本', () => {
      const raw = JSON.stringify({ level: 'WARN', message: 123 })
      const entry = parseLogPayload(raw)
      expect(entry.level).toBe('WARN')
      expect(entry.message).toBe(raw)
    })

    it('非 JSON 文本按纯文本 INFO 处理', () => {
      const entry = parseLogPayload('plain text line')
      expect(entry.level).toBe('INFO')
      expect(entry.message).toBe('plain text line')
    })

    it('空负载返回空消息且不抛错', () => {
      const entry = parseLogPayload('')
      expect(entry.message).toBe('')
      expect(LOG_LEVELS).toContain(entry.level)
    })
  })
})
