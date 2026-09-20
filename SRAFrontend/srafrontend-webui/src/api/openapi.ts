import type { OpenApiDocument } from '@/utils/schemaForm'

// 后端 OpenAPI 规范文档；开发环境经 Vite 代理（/openapi → localhost:5073）转发
export const OPENAPI_URL = '/openapi/v1.json'

export async function fetchOpenApiSpec(signal?: AbortSignal): Promise<OpenApiDocument> {
  const res = await fetch(OPENAPI_URL, { signal })
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
  return (await res.json()) as OpenApiDocument
}
