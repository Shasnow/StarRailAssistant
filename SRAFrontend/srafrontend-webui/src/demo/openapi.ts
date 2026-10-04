import spec from './v1.json?raw'
import type { OpenApiDocument } from '../utils/schemaForm'

/**
 * 演示模式共用的 OpenAPI 规范：
 * 构建期内联同目录的 v1.json 快照（?raw 导入），运行时零请求，
 * 供 state.ts 生成符合 schema 的默认配置、供 openapi 通道直接返回文档。
 */
export const demoOpenApiSpec: OpenApiDocument = JSON.parse(spec) as OpenApiDocument
