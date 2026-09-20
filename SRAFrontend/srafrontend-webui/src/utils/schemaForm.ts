// OpenAPI Schema 驱动表单的工具集：$ref 解析、类型推断、默认模型构建、字段校验

export interface SchemaNode {
  $ref?: string
  type?: string | string[]
  format?: string
  pattern?: string
  description?: string
  enum?: unknown[]
  default?: unknown
  properties?: Record<string, SchemaNode>
  items?: SchemaNode
}

export interface OpenApiDocument {
  components: {
    schemas: Record<string, SchemaNode>
  }
}

export type FieldKind = 'string' | 'integer' | 'boolean' | 'enum' | 'array' | 'object'

/** 解析 $ref（如 #/components/schemas/StartGameConfig），返回引用目标；无 $ref 时原样返回 */
export function resolveNode(doc: OpenApiDocument | null, node: SchemaNode): SchemaNode {
  if (!doc || !node?.$ref) return node
  let cur: unknown = doc
  for (const seg of node.$ref.replace(/^#\//, '').split('/')) {
    if (cur === null || typeof cur !== 'object') return node
    cur = (cur as Record<string, unknown>)[seg]
  }
  return (cur ?? node) as SchemaNode
}

function typeListOf(node: SchemaNode): string[] {
  return Array.isArray(node.type) ? node.type : node.type ? [node.type] : []
}

/** 推断字段渲染类型：对象（含 $ref/properties）→ 数组 → 枚举 → 布尔 → 整数 → 字符串 */
export function fieldKind(node: SchemaNode): FieldKind {
  if (node.$ref || node.properties) return 'object'
  const types = typeListOf(node)
  if (types.includes('array')) return 'array'
  if (node.enum?.length) return 'enum'
  if (types.includes('boolean')) return 'boolean'
  if (types.includes('integer') || types.includes('number')) return 'integer'
  return 'string'
}

/**
 * 后端将 int32 表示为 [integer, string] 联合类型并附带 pattern 校验，
 * 此类字段用文本框 + 正则校验（后端接受字符串形式整数），纯 integer 才用数字输入框
 */
export function isIntTextInput(node: SchemaNode): boolean {
  const types = typeListOf(node)
  return (types.includes('integer') || types.includes('number')) && types.includes('string')
}

/** 按字段标识（description/key）查找对应的属性 schema 节点 */
export function findProperty(node: SchemaNode, key: string): SchemaNode | undefined {
  return node.properties?.[key]
}

/** 按 schema 递归构建默认模型：对象→逐属性递归，数组→[]，布尔→false，其余→default ?? '' */
export function buildDefaultModel(doc: OpenApiDocument | null, node: SchemaNode): unknown {
  const resolved = resolveNode(doc, node)
  switch (fieldKind(resolved)) {
    case 'object': {
      const out: Record<string, unknown> = {}
      for (const [key, child] of Object.entries(resolved.properties ?? {})) {
        out[key] = buildDefaultModel(doc, child)
      }
      return out
    }
    case 'array':
      return []
    case 'boolean':
      return typeof resolved.default === 'boolean' ? resolved.default : false
    default:
      return resolved.default ?? ''
  }
}

/** 稳定序列化：键排序后 stringify，用于脏检测比较，避免键顺序差异导致误判 */
export function stableStringify(value: unknown): string {
  return JSON.stringify(value, (_k, v: unknown) => {
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      return Object.fromEntries(
        Object.entries(v as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)),
      )
    }
    return v
  })
}

/**
 * 实时校验：空值放行（schema 未声明 required）；
 * 带 pattern 的字段（含 version 的 ^-?(?:0|[1-9]\d*)$）不匹配时报错
 */
export function validateValue(node: SchemaNode, value: unknown): string | null {
  if (value === undefined || value === null || value === '') return null
  const kind = fieldKind(node)
  if ((kind === 'integer' || kind === 'string') && node.pattern) {
    if (!new RegExp(node.pattern).test(String(value))) {
      return kind === 'integer'
        ? '请输入有效整数（如 0、3、-5）'
        : `格式不正确，需匹配 ${node.pattern}`
    }
  }
  return null
}
