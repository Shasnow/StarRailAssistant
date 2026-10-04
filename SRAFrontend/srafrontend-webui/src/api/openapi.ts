import type { OpenApiDocument } from '@/utils/schemaForm'

// 后端 OpenAPI 规范文档；开发环境经 Vite 代理（/openapi → localhost:5073）转发
export const OPENAPI_URL = '/openapi/v1.json'

export async function fetchOpenApiSpec(signal?: AbortSignal): Promise<OpenApiDocument> {
  // 演示模式：直接返回构建期内联的规范（动态导入，__IS_DEMO__ 为编译期常量，
  // 正式构建下该分支与 demo/openapi chunk 一并被消除）
  if (__IS_DEMO__) {
    const { demoOpenApiSpec } = await import('@/demo/openapi')
    return demoOpenApiSpec
  }
  const res = await fetch(OPENAPI_URL, { signal })
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
  return (await res.json()) as OpenApiDocument
}
