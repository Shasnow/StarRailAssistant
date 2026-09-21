<template>
    <div class="array-editor">
        <!-- 头部：key + 描述 + 添加按钮；无 label 时仅显示添加按钮（外层已有标题） -->
        <div class="array-head">
            <div class="array-titles">
                <template v-if="label">
                    <div class="array-label">{{ label }}</div>
                    <div v-if="description" class="array-desc" :title="description">{{ description }}</div>
                </template>
            </div>
            <el-button size="small" plain :icon="Plus" @click="addItem">添加</el-button>
        </div>

        <!-- 对象条目：每个条目一个嵌套分组，内部由 SchemaForm 递归渲染 -->
        <template v-if="itemKind === 'object'">
            <div v-for="(item, i) in items" :key="i" class="array-group">
                <div class="array-group-head">
                    <span class="array-group-title">条目 {{ i + 1 }}</span>
                    <el-button size="small" type="danger" plain :icon="Delete" @click="removeItem(i)" />
                </div>
                <SchemaForm :schema="itemSchema" :doc="doc" :model-value="items[i]" :baseline="baselineItems[i]"
                    @update:model-value="setItem(i, $event)" />
            </div>
        </template>

        <!-- 基本类型条目：行内控件 + 删除 -->
        <template v-else>
            <div v-for="(item, i) in items" :key="i" class="array-row">
                <SchemaField :node="itemSchema" :doc="doc" :model-value="items[i]"
                    @update:model-value="setItem(i, $event)" />
                <el-button size="small" type="danger" plain :icon="Delete" @click="removeItem(i)" />
            </div>
        </template>

        <div v-if="!items.length" class="array-empty">暂无条目，点击「添加」新增</div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import type { OpenApiDocument, SchemaNode } from '@/utils/schemaForm'
import { buildDefaultModel, fieldKind, resolveNode } from '@/utils/schemaForm'
import SchemaField from './SchemaField.vue'
import SchemaForm from './SchemaForm.vue'

// 数组字段编辑器：从 SchemaForm 抽出的数组块，也可在顶层直接使用（如设置页的字符串列表）
const props = defineProps<{
    /** 数组 schema 节点 */
    node: SchemaNode
    doc: OpenApiDocument | null
    /** 数组 key，作为标题显示；不传则只显示添加按钮（外层已有标题） */
    label?: string
    description?: string
    /** 基线数组，供对象条目的未保存圆点对比 */
    baseline?: unknown
}>()

const model = defineModel<unknown>({ required: true })

const itemSchema = computed(() => resolveNode(props.doc, props.node.items ?? {}))
const itemKind = computed(() => fieldKind(itemSchema.value))

const items = computed<unknown[]>(() => (Array.isArray(model.value) ? model.value : []))
const baselineItems = computed<unknown[]>(() => (Array.isArray(props.baseline) ? props.baseline : []))

function setItem(index: number, value: unknown) {
    if (Array.isArray(model.value)) model.value[index] = value
}

function addItem() {
    // 模型不是数组时（字段缺失）先落一个新数组再追加，避免改动丢失在临时对象上
    const arr = Array.isArray(model.value) ? model.value : []
    arr.push(buildDefaultModel(props.doc, itemSchema.value))
    if (arr !== model.value) model.value = arr
}

function removeItem(index: number) {
    if (Array.isArray(model.value)) model.value.splice(index, 1)
}
</script>

<style scoped>
.array-editor {
    display: grid;
    gap: 10px;
}

.array-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}

.array-titles {
    display: grid;
    gap: 2px;
    min-width: 0;
}

.array-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-heading);
}

.array-desc {
    font-size: 11px;
    color: var(--color-text);
    opacity: 0.55;
}

.array-group {
    display: grid;
    gap: 10px;
    padding: 12px;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    background: var(--color-surface);
}

.array-group-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}

.array-group-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text);
    opacity: 0.75;
}

.array-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    align-items: start;
}

.array-empty {
    font-size: 12px;
    color: var(--color-text);
    opacity: 0.55;
}
</style>
