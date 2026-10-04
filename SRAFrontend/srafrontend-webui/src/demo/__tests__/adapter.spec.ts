// @vitest-environment jsdom
import type { InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ApiEnvelope } from '../../api/http'
import { createDemoAdapter } from '../adapter'
import { resetDemoState } from '../state'

/** 构造传给 adapter 的最小请求配置（默认携带 X-Access-Token，模拟已登录会话） */
function cfg(
  method: string,
  url: string,
  data?: unknown,
  signal?: AbortSignal,
): InternalAxiosRequestConfig {
  return {
    method,
    url,
    data,
    signal,
    headers: { 'X-Access-Token': 'demo-token' },
  } as InternalAxiosRequestConfig
}

/** 构造不携带认证头的请求配置（模拟未登录会话） */
function cfgAnonymous(method: string, url: string, data?: unknown): InternalAxiosRequestConfig {
  return { method, url, data, headers: {} } as InternalAxiosRequestConfig
}

const adapter = createDemoAdapter()

/** 取响应信封（adapter 直连返回的就是 R<T> 包装） */
function envelopeOf(res: { data: unknown }): ApiEnvelope {
  return res.data as ApiEnvelope
}

beforeEach(() => {
  localStorage.clear()
  resetDemoState()
})

describe('演示适配层：路由与信封', () => {
  it('GET /Configs 命中路由，返回默认配置名列表', async () => {
    const res = await adapter(cfg('get', '/Configs'))
    const env = envelopeOf(res)
    expect(res.status).toBe(200)
    expect(env.success).toBe(true)
    // 按 UTF-16 码位排序：周(U+5468) < 日(U+65E5) < 签(U+7B7E)
    expect(env.data).toEqual(['周本速刷', '日常清体力', '签到跑图'])
  })

  it('GET 单个配置：命中已有配置名（URL 编码的中文名解码）', async () => {
    const res = await adapter(cfg('get', `/Configs/${encodeURIComponent('日常清体力')}`))
    const env = envelopeOf(res)
    expect(env.success).toBe(true)
    expect(env.data).toMatchObject({ name: '日常清体力' })
  })

  it('POST 创建配置成功返回 200 信封', async () => {
    const res = await adapter(cfg('post', `/Configs/${encodeURIComponent('新配置')}`, {}))
    const env = envelopeOf(res)
    expect(env.success).toBe(true)
    expect(env.data).toContain('已创建')
  })
})

describe('演示适配层：确定性错误', () => {
  it('重名创建返回 409（reject 携带 response，供拦截器归一化）', async () => {
    await expect(
      adapter(cfg('post', `/Configs/${encodeURIComponent('日常清体力')}`, {})),
    ).rejects.toMatchObject({ response: { status: 409 } })
  })

  it('读取不存在的配置返回 404', async () => {
    await expect(
      adapter(cfg('get', `/Configs/${encodeURIComponent('不存在的配置')}`)),
    ).rejects.toMatchObject({ response: { status: 404 } })
  })

  it('配置名含非法字符返回 400', async () => {
    await expect(
      adapter(cfg('post', `/Configs/${encodeURIComponent('坏/名字')}`, {})),
    ).rejects.toMatchObject({ response: { status: 400 } })
  })
})

describe('演示适配层：任务与未模拟接口', () => {
  it('运行中任务的 status 返回 demo 模式标记', async () => {
    const run = await adapter(cfg('post', '/Task/run', { configName: '日常清体力' }))
    expect(envelopeOf(run).success).toBe(true)

    const status = await adapter(cfg('get', '/Task/status'))
    const env = envelopeOf(status)
    expect(env.success).toBe(true)
    expect(env.data).toMatchObject({ status: 'running', mode: 'demo' })
  })

  it('未匹配路由返回 success=false 的未模拟提示（不发真实请求）', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const res = await adapter(cfg('get', '/Not/Implemented'))
    const env = envelopeOf(res)
    expect(env.success).toBe(false)
    expect(env.message).toContain('未模拟')
    warn.mockRestore()
  })
})

describe('演示适配层：请求取消', () => {
  it('延迟期间 abort → 以 ERR_CANCELED 拒绝', async () => {
    const controller = new AbortController()
    const promise = adapter(cfg('get', '/Configs', undefined, controller.signal))
    controller.abort()
    await expect(promise).rejects.toMatchObject({ code: 'ERR_CANCELED' })
  })
})

describe('演示适配层：认证拦截（模拟启用认证的后端）', () => {
  it('未携带 X-Access-Token 的业务请求返回 401', async () => {
    await expect(adapter(cfgAnonymous('get', '/Configs'))).rejects.toMatchObject({
      response: { status: 401 },
    })
  })

  it('携带任意非空 token 的业务请求正常通过', async () => {
    const res = await adapter(cfg('get', '/Configs'))
    expect(res.status).toBe(200)
  })

  it('POST /auth 免带头：非空 token 校验通过', async () => {
    const res = await adapter(cfgAnonymous('post', '/auth', { token: 'any-token' }))
    const env = envelopeOf(res)
    expect(res.status).toBe(200)
    expect(env.success).toBe(true)
  })

  it('POST /auth 免带头：空 token 返回 401', async () => {
    await expect(adapter(cfgAnonymous('post', '/auth', { token: '  ' }))).rejects.toMatchObject({
      response: { status: 401 },
    })
  })
})
